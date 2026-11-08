from collections import Counter
from datetime import timedelta
from hashlib import sha256
from itertools import combinations, islice
import logging
from math import ceil

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone

from .models import Pedido, Produto, Venda


logger = logging.getLogger(__name__)
RECOMMENDATION_REVISION_KEY = 'miracommerce:recommendation:revision'


def _cache_key(prefix, *args):
    raw = ':'.join(str(arg) for arg in args)
    suffix = sha256(raw.encode('utf-8')).hexdigest()[:24] if raw else 'base'
    return f'miracommerce:{prefix}:{suffix}'


def _normalizar_regras(regras):
    """Normaliza dados de cache para uma estrutura simples e serializável."""
    return [
        {
            **regra,
            'antecedents': [int(produto_id) for produto_id in regra.get('antecedents', [])],
            'consequents': [int(produto_id) for produto_id in regra.get('consequents', [])],
        }
        for regra in regras
    ]


def _guardar_regras(cache_key, regras):
    """Armazena inclusive o resultado vazio e invalida sugestões derivadas."""
    regras = _normalizar_regras(regras)
    cache.set(cache_key, regras, timeout=getattr(settings, 'RECOMENDACAO_CACHE_TIMEOUT', 3600))
    cache.set(RECOMMENDATION_REVISION_KEY, timezone.now().isoformat(), timeout=None)
    return regras


def _iter_transacoes_de_pedidos():
    """Lê pedidos pagos por blocos, sem materializar o histórico inteiro."""
    limite = max(1, int(getattr(settings, 'RECOMMENDATION_MAX_TRANSACTIONS', 20000)))
    dias = int(getattr(settings, 'RECOMMENDATION_LOOKBACK_DAYS', 365))
    pedidos = Pedido.objects.filter(status=Pedido.Status.PAID)
    if dias > 0:
        pedidos = pedidos.filter(data_criacao__gte=timezone.now() - timedelta(days=dias))
    pedidos = pedidos.order_by('-data_criacao')[:limite].prefetch_related('itens')

    max_itens = max(2, int(getattr(settings, 'RECOMMENDATION_MAX_ITEMS_PER_TRANSACTION', 50)))
    for pedido in pedidos.iterator(chunk_size=200):
        produtos = {item.produto_id for item in pedido.itens.all() if item.produto_id}
        if len(produtos) > max_itens:
            logger.warning(
                'Pedido %s ignorado nas recomendações: excede o limite de %s produtos.',
                pedido.pk,
                max_itens,
            )
            continue
        if produtos:
            yield produtos


def _iter_transacoes_legadas():
    """Compatibilidade para vendas antigas sem ItemPedido associado."""
    limite = max(1, int(getattr(settings, 'RECOMMENDATION_MAX_TRANSACTIONS', 20000)))
    dias = int(getattr(settings, 'RECOMMENDATION_LOOKBACK_DAYS', 365))
    vendas = Venda.objects.filter(pedido__isnull=True)
    if dias > 0:
        vendas = vendas.filter(data_venda__gte=timezone.now() - timedelta(days=dias))
    vendas = vendas.order_by('id_transacao', 'produto_id').values_list('id_transacao', 'produto_id').iterator(chunk_size=1000)

    transacao_atual = None
    produtos = set()
    total = 0
    for id_transacao, produto_id in vendas:
        if transacao_atual is not None and id_transacao != transacao_atual:
            if produtos:
                yield produtos
                total += 1
                if total >= limite:
                    return
            produtos = set()
        transacao_atual = id_transacao
        if produto_id:
            produtos.add(produto_id)
    if produtos and total < limite:
        yield produtos


def _transacoes_para_recomendacao():
    """Une os pedidos atuais ao histórico legado, sem duplicar checkouts novos."""
    yield from _iter_transacoes_de_pedidos()
    yield from _iter_transacoes_legadas()


def gerar_regras_associacao(force_refresh=False, allow_compute=True, raise_errors=False):
    """Gera regras de pares sem matriz produto × transação em memória.

    As contagens são atualizadas uma transação de cada vez. Isso mantém a memória
    proporcional ao número de produtos e pares frequentes, com janela temporal e
    teto de transações configuráveis.
    """
    cache_key = _cache_key('regras_associacao_v3_pares')
    if force_refresh:
        cache.delete(cache_key)

    cached_rules = cache.get(cache_key)
    if cached_rules is not None:
        return _normalizar_regras(cached_rules)
    if not allow_compute:
        return []

    try:
        ocorrencias_produto = Counter()
        ocorrencias_par = Counter()
        total_transacoes = 0
        limite_transacoes = max(1, int(getattr(settings, 'RECOMMENDATION_MAX_TRANSACTIONS', 20000)))
        for produtos in islice(_transacoes_para_recomendacao(), limite_transacoes):
            produtos = sorted(set(int(produto) for produto in produtos))
            if not produtos:
                continue
            total_transacoes += 1
            ocorrencias_produto.update(produtos)
            ocorrencias_par.update(combinations(produtos, 2))

        if total_transacoes < 2 or not ocorrencias_par:
            return _guardar_regras(cache_key, [])

        suporte_minimo = max(0.0, float(getattr(settings, 'RECOMMENDATION_MIN_SUPPORT', 0.01)))
        ocorrencias_minimas = max(1, ceil(total_transacoes * suporte_minimo))
        lift_minimo = float(getattr(settings, 'RECOMMENDATION_MIN_LIFT', 1.0))
        regras = []
        for (produto_a, produto_b), ocorrencias in ocorrencias_par.items():
            if ocorrencias < ocorrencias_minimas:
                continue
            for antecedente, consequente in ((produto_a, produto_b), (produto_b, produto_a)):
                confidence = ocorrencias / ocorrencias_produto[antecedente]
                lift = confidence / (ocorrencias_produto[consequente] / total_transacoes)
                if lift < lift_minimo:
                    continue
                regras.append({
                    'antecedents': [antecedente],
                    'consequents': [consequente],
                    'support': ocorrencias / total_transacoes,
                    'lift': lift,
                    'confidence': confidence,
                })

        regras.sort(key=lambda regra: (regra['lift'], regra['confidence'], regra['support']), reverse=True)
        regras = regras[:max(1, int(getattr(settings, 'RECOMMENDATION_MAX_RULES', 500)))]
        return _guardar_regras(cache_key, regras)
    except Exception:
        logger.exception('Erro ao gerar regras de associação.')
        if raise_errors:
            raise
        return []


def _resolver_produto_id(produto):
    """Aceita IDs e objetos; nomes ficam apenas como compatibilidade legada."""
    if isinstance(produto, Produto):
        return produto.pk
    if isinstance(produto, int) or (isinstance(produto, str) and produto.isdigit()):
        return int(produto)
    nome_legado = (str(produto or '')).strip()
    return Produto.objects.filter(nome__iexact=nome_legado).values_list('pk', flat=True).first()


def obter_recomendacoes_para_produto(produto_id, limite=4, *, retornar_ids=False):
    """Retorna IDs de produtos relacionados, usando o produto como identidade.

    ``retornar_ids=False`` preserva a resposta textual da API legada enquanto
    a vitrine e o carrinho trabalham internamente apenas com IDs.
    """
    produto_id = _resolver_produto_id(produto_id)
    if not produto_id:
        return []

    revision = cache.get(RECOMMENDATION_REVISION_KEY, 'initial')
    cache_key = _cache_key('recomendacao_produto_v3', revision, produto_id, limite, retornar_ids)
    cached_sugestoes = cache.get(cache_key)
    if cached_sugestoes is not None:
        return cached_sugestoes

    regras = gerar_regras_associacao(allow_compute=False)
    sugestoes_ids = []
    if regras:
        for regra in regras:
            if int(produto_id) in regra['antecedents']:
                sugestoes_ids.extend(regra['consequents'])
        sugestoes_ids = [item for item in dict.fromkeys(sugestoes_ids) if item != int(produto_id)][:limite]

    if not sugestoes_ids:
        ids_transacao = Venda.objects.filter(produto_id=produto_id).values_list('id_transacao', flat=True).distinct()
        if ids_transacao:
            sugestoes_ids = list(
                Venda.objects.filter(id_transacao__in=ids_transacao)
                .exclude(produto_id=produto_id)
                .values('produto_id')
                .annotate(total=Count('produto_id'))
                .order_by('-total', 'produto_id')
                .values_list('produto_id', flat=True)[:limite]
            )

    if not sugestoes_ids:
        produto = Produto.objects.filter(pk=produto_id).first()
        if produto and produto.categoria_id:
            sugestoes_ids = list(
                Produto.objects.filter(categoria_id=produto.categoria_id)
                .exclude(pk=produto_id)
                .order_by('id')
                .values_list('id', flat=True)[:limite]
            )

    if retornar_ids:
        resultado = sugestoes_ids
    else:
        nomes = dict(Produto.objects.filter(id__in=sugestoes_ids).values_list('id', 'nome'))
        resultado = [nomes[item] for item in sugestoes_ids if item in nomes]

    cache.set(cache_key, resultado, timeout=getattr(settings, 'RECOMENDACAO_CACHE_TIMEOUT', 3600))
    return resultado


def gerar_sugestoes_para_carrinho(itens, limite=3):
    """Gera as sugestões da IA para os itens do carrinho."""
    if not itens:
        return []

    sugestoes = []
    ids_no_carrinho = {item['produto'].id for item in itens}

    for item in itens:
        recomendacoes = obter_recomendacoes_para_produto(
            item['produto'].id,
            limite=limite,
            retornar_ids=True,
        )

        for produto_id_sugerido in recomendacoes:
            if produto_id_sugerido in ids_no_carrinho:
                continue

            produto_sugerido = Produto.objects.filter(pk=produto_id_sugerido).first()
            if produto_sugerido:
                sugestoes.append({
                    'produto_base': item['produto'],
                    'produto_sugerido': produto_sugerido,
                    'confianca': 90,
                })

    vistos = set()
    sugestoes_finais = []
    for sugestao in sugestoes:
        chave = sugestao['produto_sugerido'].id
        if chave not in vistos:
            vistos.add(chave)
            sugestoes_finais.append(sugestao)

    return sugestoes_finais[:limite]
