from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.db.models import Case, When, Max, Count, Sum, Avg, DecimalField, ExpressionWrapper, F, Q
from django.db.models.functions import Coalesce
from django.core.cache import cache
from django.conf import settings
from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256
import logging
from secrets import compare_digest
from uuid import UUID, uuid4
from django.contrib.auth.decorators import login_required
from django.contrib import messages 
from django.db import transaction, IntegrityError
from django.contrib.auth import login as auth_login
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST

# Importações locais
from .models import Pedido, Produto, Venda, Perfil, Categoria, SubCategoria, ZonaEntrega
from .forms import CadastroForm, DefinicoesForm
from .tasks import enqueue_recommendation_refresh
from .privacy import anonimizar_usuario, exportar_dados_usuario
from .services import (
    CarrinhoService,
    PedidoService,
    RecomendacaoService,
    RelatorioService,
)
from .notificacoes import gerar_link_whatsapp_cliente, gerar_link_whatsapp_suporte

logger = logging.getLogger(__name__)


# Imagens deliberadamente associadas a cada categoria da vitrine. A ordem da
# base de dados não deve determinar a imagem exibida nem provocar repetições.
CATEGORY_GALLERY_IMAGES = {
    'mercearia-e-despensa': 'loja/img/carousel/mercearia.jpg',
    'produtos-frescos': 'loja/img/carousel/frescos.jpg',
    'bebidas': 'loja/img/carousel/bebidas.jpg',
    'higiene-e-casa': 'loja/img/carousel/higiene.jpg',
    'matabicho': 'loja/img/carousel/matabicho.jpg',
    'frio-e-congelados': 'loja/img/carousel/frio-congelados.jpg',
}


def _cache_key(prefix, *parts):
    raw = '|'.join(str(part) for part in parts if part is not None)
    digest = sha256(raw.encode('utf-8')).hexdigest()[:24] if raw else 'base'
    return f'miracommerce:{prefix}:{digest}'


CHECKOUT_IDEMPOTENCY_SESSION_KEY = 'checkout_idempotency_key'
GUIDE_INTRO_SESSION_KEY = 'guia_introducao_vista'
GUIDE_INTRO_PENDING_SESSION_KEY = 'guia_introducao_pendente'


def _renovar_chave_checkout(request):
    """Vincula uma nova operação de checkout ao estado atual do carrinho."""
    chave = str(uuid4())
    request.session[CHECKOUT_IDEMPOTENCY_SESSION_KEY] = chave
    request.session.modified = True
    return chave


def _obter_chave_checkout(request):
    chave = request.session.get(CHECKOUT_IDEMPOTENCY_SESSION_KEY)
    return chave or _renovar_chave_checkout(request)


def _get_categorias_menu_cache():
    cache_key = _cache_key('categorias_menu_v3')
    categoria_ids = cache.get(cache_key)
    if categoria_ids is None:
        categoria_ids = list(
            Categoria.objects.exclude(nome__icontains='teste').order_by('id').values_list('id', flat=True)
        )
        cache.set(cache_key, categoria_ids, timeout=getattr(settings, 'CACHE_TIMEOUT', 300))

    categorias = Categoria.objects.prefetch_related('subcategorias').filter(id__in=categoria_ids)
    categorias_por_id = {categoria.id: categoria for categoria in categorias}
    return [categorias_por_id[categoria_id] for categoria_id in categoria_ids if categoria_id in categorias_por_id]


def _get_categorias_vitrine(categorias):
    """Acopla o conteúdo de cada categoria ao seu visual editorial único."""
    return [
        {
            'categoria': categoria,
            'imagem': CATEGORY_GALLERY_IMAGES.get(categoria.slug),
        }
        for categoria in categorias
    ]


def _get_produtos_home_page(
    termo_busca=None,
    categoria_id=None,
    subcategoria_id=None,
    ordenar='padrao',
    preco_min=None,
    preco_max=None,
    apenas_promocao=False,
    pagina=1,
):
    """Obtém somente uma página de IDs, preservando dados de produto frescos, ordenados e filtrados."""
    qs = Produto.objects.select_related('categoria', 'subcategoria').filter(
        Q(data_validade__isnull=True) | Q(data_validade__gte=date.today())
    ).exclude(categoria__nome__icontains='teste')

    if termo_busca:
        qs = qs.filter(nome__icontains=termo_busca)
    if categoria_id:
        qs = qs.filter(categoria_id=categoria_id)
    if subcategoria_id:
        qs = qs.filter(subcategoria_id=subcategoria_id)

    # Anotação de preço final de venda (considera preço promocional se produto estiver em promoção)
    preco_final_expr = Case(
        When(em_promocao=True, preco_promocional__isnull=False, then=F('preco_promocional')),
        default=F('preco'),
        output_field=DecimalField(max_digits=10, decimal_places=2),
    )
    qs = qs.annotate(preco_final=preco_final_expr)

    # Filtros de faixa de preço
    if preco_min:
        try:
            val_min = Decimal(str(preco_min).replace(',', '.'))
            if val_min >= 0:
                qs = qs.filter(preco_final__gte=val_min)
        except (ValueError, TypeError, ArithmeticError):
            pass

    if preco_max:
        try:
            val_max = Decimal(str(preco_max).replace(',', '.'))
            if val_max >= 0:
                qs = qs.filter(preco_final__lte=val_max)
        except (ValueError, TypeError, ArithmeticError):
            pass

    # Filtro de apenas produtos em promoção
    if apenas_promocao:
        qs = qs.filter(em_promocao=True)

    # Mapeamento determinístico de ordenação
    ORDER_MAP = {
        'menor_preco': ('preco_final', 'id'),
        'maior_preco': ('-preco_final', 'id'),
        'nome_asc': ('nome', 'id'),
        'nome_desc': ('-nome', 'id'),
        'em_promocao': ('-em_promocao', 'preco_final', 'id'),
        'mais_novos': ('-id',),
        'padrao': ('id',),
    }
    ordem_campos = ORDER_MAP.get(ordenar, ('id',))
    qs = qs.order_by(*ordem_campos)

    paginador = Paginator(qs, getattr(settings, 'CATALOG_PAGE_SIZE', 24))
    pagina_atual = paginador.get_page(pagina)
    cache_key = _cache_key(
        'home_produtos_v5',
        (termo_busca or '').strip().lower(),
        categoria_id or '',
        subcategoria_id or '',
        ordenar or 'padrao',
        str(preco_min or '').strip(),
        str(preco_max or '').strip(),
        '1' if apenas_promocao else '',
        pagina_atual.number,
    )
    produto_ids = cache.get(cache_key)
    if produto_ids is None:
        produto_ids = list(pagina_atual.object_list.values_list('id', flat=True))
        cache.set(cache_key, produto_ids, timeout=getattr(settings, 'CACHE_TIMEOUT', 300))

    produtos = Produto.objects.select_related('categoria', 'subcategoria').filter(id__in=produto_ids)
    produtos_por_id = {produto.id: produto for produto in produtos}
    pagina_atual.object_list = [
        produtos_por_id[produto_id]
        for produto_id in produto_ids
        if produto_id in produtos_por_id
    ]
    return pagina_atual.object_list, pagina_atual


# --- 1. VITRINE PRINCIPAL & DASHBOARD IA ---
def home(request, categoria_id=None, subcategoria_id=None):
    # A primeira abertura da página principal funciona como uma pequena
    # receção ao serviço. A preferência permanece somente nesta sessão do
    # navegador; o Guia continua disponível pelo menu a qualquer momento.
    if (
        categoria_id is None
        and subcategoria_id is None
        and not request.GET
        and not (request.user.is_authenticated and request.user.is_staff)
        and not request.session.get(GUIDE_INTRO_SESSION_KEY)
    ):
        request.session[GUIDE_INTRO_SESSION_KEY] = True
        request.session[GUIDE_INTRO_PENDING_SESSION_KEY] = True
        return redirect('guia')

    termo_busca = request.GET.get('q')
    categoria_ativa = None
    subcategoria_ativa = None

    if categoria_id:
        categoria_ativa = get_object_or_404(Categoria, id=categoria_id)

    if subcategoria_id:
        subcategoria_ativa = get_object_or_404(SubCategoria, id=subcategoria_id)

    # Parâmetros de ordenação e filtro de preço
    ordenar = request.GET.get('ordenar', 'padrao')
    preco_min = request.GET.get('preco_min', '').strip()
    preco_max = request.GET.get('preco_max', '').strip()
    apenas_promocao = request.GET.get('promo', '').strip().lower() in ('1', 'true', 'sim')

    # Validação para inputs limpos no formulário
    try:
        if preco_min:
            Decimal(preco_min.replace(',', '.'))
    except Exception:
        preco_min = ''

    try:
        if preco_max:
            Decimal(preco_max.replace(',', '.'))
    except Exception:
        preco_max = ''

    produtos, pagina_produtos = _get_produtos_home_page(
        termo_busca=termo_busca,
        categoria_id=categoria_id,
        subcategoria_id=subcategoria_id,
        ordenar=ordenar,
        preco_min=preco_min,
        preco_max=preco_max,
        apenas_promocao=apenas_promocao,
        pagina=request.GET.get('pagina', 1),
    )

    if categoria_ativa and subcategoria_ativa and subcategoria_ativa.categoria_id != categoria_ativa.id:
        produtos = [produto for produto in produtos if produto.categoria_id == categoria_ativa.id and produto.subcategoria_id == subcategoria_ativa.id]

    # Construção de URLs e estado de filtros preservando contexto
    get_params = request.GET.copy()
    if 'pagina' in get_params:
        del get_params['pagina']

    def _gerar_url_com_params(overrides=None, remover=None):
        p = get_params.copy()
        if remover:
            for k in remover:
                if k in p:
                    del p[k]
        if overrides:
            for k, v in overrides.items():
                if v is not None and v != '':
                    p[k] = str(v)
                elif k in p:
                    del p[k]
        qs_str = p.urlencode()
        return f"{request.path}?{qs_str}#produtos-ancora" if qs_str else f"{request.path}#produtos-ancora"

    presets_preco = [
        {
            'label': 'Todos os Preços',
            'url': _gerar_url_com_params(remover=['preco_min', 'preco_max']),
            'ativo': not preco_min and not preco_max,
        },
        {
            'label': 'Até 5.000 Kz',
            'url': _gerar_url_com_params(overrides={'preco_min': '', 'preco_max': '5000'}),
            'ativo': preco_min == '' and preco_max == '5000',
        },
        {
            'label': '5.000 - 15.000 Kz',
            'url': _gerar_url_com_params(overrides={'preco_min': '5000', 'preco_max': '15000'}),
            'ativo': preco_min == '5000' and preco_max == '15000',
        },
        {
            'label': '15.000 - 30.000 Kz',
            'url': _gerar_url_com_params(overrides={'preco_min': '15000', 'preco_max': '30000'}),
            'ativo': preco_min == '15000' and preco_max == '30000',
        },
        {
            'label': '+30.000 Kz',
            'url': _gerar_url_com_params(overrides={'preco_min': '30000', 'preco_max': ''}),
            'ativo': preco_min == '30000' and preco_max == '',
        },
    ]

    filtros_ativos = []
    if termo_busca:
        filtros_ativos.append({
            'chave': 'q',
            'label': f'Busca: "{termo_busca}"',
            'url_remover': _gerar_url_com_params(remover=['q']),
        })
    if preco_min and preco_max:
        filtros_ativos.append({
            'chave': 'preco_range',
            'label': f'{preco_min} Kz – {preco_max} Kz',
            'url_remover': _gerar_url_com_params(remover=['preco_min', 'preco_max']),
        })
    elif preco_min:
        filtros_ativos.append({
            'chave': 'preco_min',
            'label': f'A partir de {preco_min} Kz',
            'url_remover': _gerar_url_com_params(remover=['preco_min']),
        })
    elif preco_max:
        filtros_ativos.append({
            'chave': 'preco_max',
            'label': f'Até {preco_max} Kz',
            'url_remover': _gerar_url_com_params(remover=['preco_max']),
        })
    if apenas_promocao:
        filtros_ativos.append({
            'chave': 'promo',
            'label': '🔥 Em Promoção',
            'url_remover': _gerar_url_com_params(remover=['promo']),
        })
    if ordenar and ordenar != 'padrao':
        nomes_ordem = {
            'menor_preco': 'Menor Preço',
            'maior_preco': 'Maior Preço',
            'nome_asc': 'Nome: A a Z',
            'nome_desc': 'Nome: Z a A',
            'em_promocao': 'Ofertas Primeiro',
            'mais_novos': 'Mais Recentes',
        }
        if ordenar in nomes_ordem:
            filtros_ativos.append({
                'chave': 'ordenar',
                'label': f'Ordem: {nomes_ordem[ordenar]}',
                'url_remover': _gerar_url_com_params(remover=['ordenar']),
            })

    # Promoções são atualizadas pelo worker agendado, nunca durante um GET.
    hoje = date.today()
    limite_validade = hoje + timedelta(days=90)

    categorias = _get_categorias_menu_cache()

    contexto = {
        'produtos': produtos,
        'hoje': hoje,
        'categorias': categorias,
        'categorias_vitrine': _get_categorias_vitrine(categorias),
        'categoria_ativa': categoria_ativa,
        'subcategoria_ativa': subcategoria_ativa,
        'pagina_produtos': pagina_produtos,
        'termo_busca': termo_busca,
        'ordenar': ordenar,
        'preco_min': preco_min,
        'preco_max': preco_max,
        'apenas_promocao': apenas_promocao,
        'presets_preco': presets_preco,
        'filtros_ativos': filtros_ativos,
        'querystring_base': get_params.urlencode(),
        'url_limpar_tudo': f"{request.path}#produtos-ancora",
        'total_produtos': pagina_produtos.paginator.count,
    }

    # --- LÓGICA DO DASHBOARD ADMINISTRATIVO ---
    if request.user.is_authenticated and request.user.is_staff:
        contexto['total_vendas_quantidade'] = Venda.objects.values('id_transacao').distinct().count()
        trinta_dias_atras = timezone.now() - timedelta(days=30)
        contexto['novos_clientes_count'] = User.objects.filter(date_joined__gte=trinta_dias_atras).count()

        valor_linha = ExpressionWrapper(
            F('quantidade') * Coalesce(
                'preco_unitario',
                'produto__preco',
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
        total_financeiro = Venda.objects.aggregate(total=Sum(valor_linha))['total'] or Decimal('0.00')
        total_transacoes = contexto['total_vendas_quantidade']
        contexto['total_receita'] = total_financeiro
        contexto['ticket_medio'] = total_financeiro / total_transacoes if total_transacoes > 0 else 0
        
        contexto['alertas'] = Produto.objects.filter(quantidade_estoque__lte=5)
        contexto['alertas_validade'] = Produto.objects.filter(data_validade__range=[hoje, limite_validade]).order_by('data_validade')[:5]

        # Pedidos Recentes para o Painel da Operação
        contexto['pedidos_recentes'] = (
            Pedido.objects.all()
            .select_related('usuario')
            .prefetch_related('itens__produto')
            .order_by('-data_criacao')[:6]
        )
        contexto['pedidos_pendentes_count'] = Pedido.objects.filter(
            status__in=[Pedido.Status.PAID, Pedido.Status.PROCESSING]
        ).count()

        try:
            semana_atual = timezone.now() - timedelta(days=7)
            contexto['top_vendidos'] = (
                Venda.objects
                .filter(data_venda__gte=semana_atual)
                .values('produto__nome')
                .annotate(total=Sum('quantidade'))
                .order_by('-total', 'produto__nome')[:5]
            )
            if contexto['top_vendidos']:
                contexto['tendencia'] = contexto['top_vendidos'][0]

            regras = RecomendacaoService.regras(allow_compute=False)
            if not regras:
                enqueue_recommendation_refresh()
            sugestoes_lista = []
            if regras:
                ids_regras = {
                    int(produto_id)
                    for coluna in ('antecedents', 'consequents')
                    for regra in regras[:3]
                    for produto_id in regra[coluna]
                }
                nomes_regras = dict(
                    Produto.objects.filter(id__in=ids_regras).values_list('id', 'nome')
                )
                for regra in regras[:3]:
                    antecedente_id = regra['antecedents'][0]
                    consequente_id = regra['consequents'][0]
                    antecedente = nomes_regras.get(antecedente_id, f'Produto #{antecedente_id}')
                    consequente = nomes_regras.get(consequente_id, f'Produto #{consequente_id}')
                    sugestoes_lista.append(f"Quem compra {antecedente} costuma levar {consequente}")
            contexto['sugestoes'] = sugestoes_lista
        except Exception:
            logger.exception('Erro ao montar sugestões do painel administrativo.')
            contexto['sugestoes'] = ["IA processando novos dados..."]

    return render(request, 'loja/index.html', contexto)

# --- 2. GESTÃO DO CARRINHO ---
def exibir_carrinho(request):
    carrinho = request.session.get('carrinho', {})

    # Carregar zonas ativas para seleção de entrega
    zonas_disponiveis = list(ZonaEntrega.objects.filter(ativo=True).order_by('ordem', 'taxa', 'nome'))
    zona_id_sessao = request.session.get('zona_entrega_id')
    zona_selecionada = None
    if zona_id_sessao:
        zona_selecionada = next((z for z in zonas_disponiveis if str(z.id) == str(zona_id_sessao)), None)
    if not zona_selecionada and zonas_disponiveis:
        zona_selecionada = zonas_disponiveis[0]
        request.session['zona_entrega_id'] = zona_selecionada.id

    resumo = CarrinhoService.carregar(carrinho, zona=zona_selecionada)
    itens = resumo['itens']
    subtotal = resumo['subtotal']
    frete = resumo['frete']
    total = resumo['total']

    sugestoes_ia = []
    try:
        sugestoes_ia = RecomendacaoService.para_carrinho(itens, limite=3)
    except Exception:
        logger.exception('Erro ao gerar sugestões para o carrinho.')

    saldo_bonus = 0
    if request.user.is_authenticated:
        perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
        saldo_bonus = perfil.saldo_bonus

    return render(request, 'loja/carrinho.html', {
        'itens': itens,
        'subtotal': subtotal,
        'frete': frete,
        'total': total,
        'zonas_disponiveis': zonas_disponiveis,
        'zona_selecionada': zona_selecionada,
        'saldo_bonus': saldo_bonus,
        'sugestoes_ia': sugestoes_ia,
        # A chave nasce antes do POST e pertence à versão atual do carrinho.
        # Assim, abas e cliques concorrentes usam a mesma operação.
        'checkout_idempotency_key': _obter_chave_checkout(request) if itens else None,
    })

@require_POST
def definir_zona_entrega(request):
    zona_id = request.POST.get('zona_id')
    zona = ZonaEntrega.objects.filter(id=zona_id, ativo=True).first()
    if not zona:
        return JsonResponse({'ok': False, 'message': 'Zona de entrega não encontrada.'}, status=400)

    request.session['zona_entrega_id'] = zona.id
    carrinho = request.session.get('carrinho', {})
    resumo = CarrinhoService.carregar(carrinho, zona=zona)

    return JsonResponse({
        'ok': True,
        'zona_id': zona.id,
        'zona_nome': zona.nome,
        'taxa': f"{zona.taxa:.2f}",
        'subtotal': f"{resumo['subtotal']:.2f}",
        'frete': f"{resumo['frete']:.2f}",
        'total': f"{resumo['total']:.2f}",
        'prazo_estimado': zona.prazo_estimado,
        'descricao': zona.descricao,
    })

@require_POST
def adicionar_ao_carrinho(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id)
    carrinho = request.session.get('carrinho', {})
    p_id = str(produto_id)
    
    if carrinho.get(p_id, 0) + 1 <= produto.quantidade_estoque:
        carrinho[p_id] = carrinho.get(p_id, 0) + 1
        request.session['carrinho'] = carrinho
        checkout_key = _renovar_chave_checkout(request)
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'message': f'{produto.nome} no cesto!',
                'total_itens': sum(carrinho.values()),
                'idempotency_key': checkout_key,
            })
            
        messages.success(request, f"{produto.nome} adicionado ao cesto!")
    else:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'message': 'Stock insuficiente!'}, status=400)
        messages.warning(request, "Stock insuficiente!")
        
    return redirect('exibir_carrinho') # Redireciona para o carrinho para ver a mudança

@require_POST
def editar_carrinho(request, produto_id, acao):
    carrinho = dict(request.session.get('carrinho', {}))
    carrinho_anterior = carrinho.copy()
    p_id = str(produto_id)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    if p_id in carrinho:
        if acao == 'aumentar':
            p = get_object_or_404(Produto, id=produto_id)
            if carrinho[p_id] < p.quantidade_estoque: carrinho[p_id] += 1
        elif acao == 'diminuir':
            carrinho[p_id] -= 1
            if carrinho[p_id] <= 0: del carrinho[p_id]
    request.session['carrinho'] = carrinho
    checkout_key = (
        _renovar_chave_checkout(request)
        if carrinho != carrinho_anterior
        else _obter_chave_checkout(request)
    )

    if is_ajax:
        zona_id = request.session.get('zona_entrega_id')
        zona = ZonaEntrega.objects.filter(id=zona_id, ativo=True).first() if zona_id else None
        resumo = CarrinhoService.carregar(carrinho, zona=zona)
        itens = resumo['itens']
        subtotal = resumo['subtotal']
        frete = resumo['frete']
        total = resumo['total']
        item_atual = next((item for item in itens if item['produto'].id == produto_id), None)
        return JsonResponse({
            'ok': True,
            'produto_id': produto_id,
            'quantidade': item_atual['quantidade'] if item_atual else 0,
            'item_subtotal': f"{item_atual['subtotal']:.2f}" if item_atual else '0.00',
            'subtotal': f'{subtotal:.2f}',
            'frete': f'{frete:.2f}',
            'total': f'{total:.2f}',
            'total_itens': sum(carrinho.values()),
            'line_count': len(itens),
            'removed': item_atual is None,
            'idempotency_key': checkout_key,
        })

    return redirect('exibir_carrinho')

@require_POST
def remover_do_carrinho(request, produto_id):
    carrinho = dict(request.session.get('carrinho', {}))
    if str(produto_id) in carrinho:
        del carrinho[str(produto_id)]
    request.session['carrinho'] = carrinho
    _renovar_chave_checkout(request)
    return redirect('exibir_carrinho')

# --- 3. FINALIZAÇÃO ---
@require_POST
@login_required
@transaction.atomic
def processar_finalizacao_compra(request):
    carrinho = request.session.get('carrinho', {})
    if not carrinho:
        messages.info(request, "O seu cesto está vazio.")
        return redirect('home')

    idempotency_key = request.POST.get('idempotency_key', '')
    try:
        UUID(str(idempotency_key))
    except (TypeError, ValueError):
        messages.error(request, 'A sessão de checkout expirou. Revise o cesto e tente novamente.')
        return redirect('exibir_carrinho')
    session_key = request.session.get(CHECKOUT_IDEMPOTENCY_SESSION_KEY, '')
    if not session_key or not compare_digest(str(idempotency_key), str(session_key)):
        messages.error(request, 'O cesto foi atualizado. Revise-o antes de finalizar a compra.')
        return redirect('exibir_carrinho')

    zona_id = request.POST.get('zona_entrega_id') or request.session.get('zona_entrega_id')
    endereco_entrega = request.POST.get('endereco_entrega', '').strip()

    try:
        total_venda, _ = PedidoService.finalizar(
            request.user,
            carrinho,
            zona_id=zona_id,
            endereco_entrega=endereco_entrega,
            idempotency_key=idempotency_key,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('exibir_carrinho')

    request.session['carrinho'] = {}
    request.session.pop(CHECKOUT_IDEMPOTENCY_SESSION_KEY, None)
    request.session.pop('zona_entrega_id', None)
    messages.success(request, "Compra finalizada com sucesso! Acompanhe o status do seu pedido abaixo.")
    pedido_recente = Pedido.objects.filter(usuario=request.user, idempotency_key=idempotency_key).first()
    if pedido_recente:
        return redirect('detalhe_pedido', pedido_id=pedido_recente.id)
    return redirect('meus_pedidos')


# --- 3.1. RASTREIO E GESTÃO DE PEDIDOS ---
@login_required
def meus_pedidos(request):
    """Exibe os pedidos do utilizador com histórico e atalhos de rastreio.

    Para administradores (staff), exibe também a visão geral de todos os
    pedidos realizados pelos clientes na loja.
    """
    modo = request.GET.get('modo')
    is_staff = request.user.is_staff

    # Se for staff e não especificar 'meus', exibe os pedidos dos clientes
    ver_todos = is_staff and modo != 'meus'

    if ver_todos:
        pedidos_qs = (
            Pedido.objects.all()
            .select_related('usuario', 'usuario__perfil')
            .prefetch_related('itens__produto', 'pagamento')
            .order_by('-data_criacao')
        )
    else:
        pedidos_qs = (
            Pedido.objects.filter(usuario=request.user)
            .select_related('usuario')
            .prefetch_related('itens__produto', 'pagamento')
            .order_by('-data_criacao')
        )

    termo_busca = request.GET.get('q', '').strip()
    if termo_busca and ver_todos:
        pedidos_qs = pedidos_qs.filter(
            Q(usuario__username__icontains=termo_busca) |
            Q(usuario__email__icontains=termo_busca) |
            Q(id__icontains=termo_busca)
        )

    paginador = Paginator(pedidos_qs, 10)
    pagina = paginador.get_page(request.GET.get('pagina', 1))

    total_pedidos_loja = Pedido.objects.count() if is_staff else 0
    total_pedidos_pessoais = Pedido.objects.filter(usuario=request.user).count()

    return render(request, 'loja/meus_pedidos.html', {
        'pagina_pedidos': pagina,
        'total_pedidos': pedidos_qs.count(),
        'modo_ver_todos': ver_todos,
        'total_pedidos_loja': total_pedidos_loja,
        'total_pedidos_pessoais': total_pedidos_pessoais,
        'termo_busca': termo_busca,
    })


@login_required
def detalhe_pedido(request, pedido_id):
    """Exibe a timeline visual interativa e os detalhes completos de um pedido."""
    filtro = {'id': pedido_id}
    if not request.user.is_staff:
        filtro['usuario'] = request.user

    pedido = get_object_or_404(
        Pedido.objects.prefetch_related('itens__produto', 'historico_status__usuario'),
        **filtro
    )

    perfil = getattr(pedido.usuario, 'perfil', None)
    pagamento = getattr(pedido, 'pagamento', None)
    etapas = pedido.obter_etapas_timeline()
    historico = pedido.historico_status.all().order_by('-criado_em')

    base_url = request.build_absolute_uri('/')
    whatsapp_link_cliente = gerar_link_whatsapp_cliente(pedido, base_url)
    whatsapp_link_suporte = gerar_link_whatsapp_suporte(pedido, base_url)

    return render(request, 'loja/rastreio_pedido.html', {
        'pedido': pedido,
        'perfil': perfil,
        'pagamento': pagamento,
        'etapas': etapas,
        'historico': historico,
        'whatsapp_link_cliente': whatsapp_link_cliente,
        'whatsapp_link_suporte': whatsapp_link_suporte,
        'status_choices': Pedido.Status.choices,
    })


@login_required
@require_POST
def alterar_status_pedido_staff(request, pedido_id):
    """Permite aos operadores staff alterarem o estado do pedido diretamente no rastreio."""
    if not request.user.is_staff:
        messages.error(request, "Apenas administradores e operadores podem alterar o estado do pedido.")
        return redirect('detalhe_pedido', pedido_id=pedido_id)

    pedido = get_object_or_404(Pedido, id=pedido_id)
    novo_status = request.POST.get('novo_status')

    valid_statuses = [s[0] for s in Pedido.Status.choices]
    if novo_status not in valid_statuses:
        messages.error(request, "Estado selecionado inválido.")
        return redirect('detalhe_pedido', pedido_id=pedido.id)

    if novo_status != pedido.status:
        pedido._status_actor_id = request.user.pk
        pedido.status = novo_status
        pedido.save()
        messages.success(
            request,
            f"Estado do pedido atualizado para '{pedido.get_status_display()}' com sucesso! A notificação foi enviada ao cliente."
        )
    else:
        messages.info(request, "O pedido já se encontra no estado selecionado.")

    return redirect('detalhe_pedido', pedido_id=pedido.id)

# --- 4. RELATÓRIOS E UTILITÁRIOS ---
def _filtros_relatorio(request):
    inicio = parse_date(request.GET.get('inicio', ''))
    fim = parse_date(request.GET.get('fim', ''))
    if inicio and fim and inicio > fim:
        inicio, fim = fim, inicio
    return inicio, fim


@login_required
def relatorio_vendas(request):
    if not request.user.is_staff:
        return HttpResponse('Não autorizado', status=403)
    inicio, fim = _filtros_relatorio(request)
    vendas = RelatorioService.filtrar_vendas(inicio, fim)
    resumo = RelatorioService.calcular_resumo(vendas)
    pagina = Paginator(vendas, 25).get_page(request.GET.get('pagina'))
    return render(request, 'loja/relatorios.html', {
        'pagina': pagina,
        'inicio': inicio,
        'fim': fim,
        'total_registros': vendas.count(),
        'resumo': resumo,
    })


@login_required
def exportar_relatorio_vendas(request, formato):
    if not request.user.is_staff:
        return HttpResponse('Não autorizado', status=403)
    inicio, fim = _filtros_relatorio(request)
    vendas = RelatorioService.filtrar_vendas(inicio, fim)
    sufixo = f'_{inicio:%Y%m%d}' if inicio else ''
    if fim:
        sufixo += f'_{fim:%Y%m%d}'
    if formato == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="relatorio_vendas{sufixo}.csv"'
        return RelatorioService.gerar_csv(response, vendas)
    if formato == 'excel':
        response = HttpResponse(content_type='application/vnd.ms-excel; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="relatorio_vendas{sufixo}.xls"'
        return RelatorioService.gerar_excel(response, vendas)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="relatorio_vendas{sufixo or "_completo"}.pdf"'
    return RelatorioService.gerar_pdf(response, vendas, inicio=inicio, fim=fim, usuario=request.user)


def privacidade(request):
    return render(request, 'loja/privacidade.html', {
        'data_retention_days': getattr(settings, 'DATA_RETENTION_DAYS', 1825),
    })


@login_required
def exportar_dados(request):
    response = JsonResponse(exportar_dados_usuario(request.user), json_dumps_params={'ensure_ascii': False})
    response['Content-Disposition'] = 'attachment; filename="meus_dados.json"'
    return response


@login_required
@require_POST
def excluir_dados(request):
    if request.user.is_staff:
        messages.error(request, 'Contas administrativas devem ser removidas pelo responsável pela organização.')
        return redirect('privacidade')
    anonimizar_usuario(request.user)
    request.session.flush()
    return redirect('home')

def cadastro(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                auth_login(request, user)
                messages.success(request, f"Bem-vindo, {user.username}!")
                return redirect('home')
            except IntegrityError:
                form.add_error('username', 'Este nome de utilizador ou e-mail já se encontra registado.')
    else:
        form = CadastroForm()
    return render(request, 'loja/cadastro.html', {'form': form})

def carrinho_global(request):
    try:
        carrinho = request.session.get('carrinho', {})
        total = sum(carrinho.values())
    except (AttributeError, TypeError, ValueError):
        total = 0
    return {
        'total_itens_carrinho': total,
        'categorias_menu': _get_categorias_menu_cache(),
    }

def sobre(request): return render(request, 'loja/sobre.html')
def ajuda(request): return render(request, 'loja/ajuda.html')
def faq(request): return render(request, 'loja/faq.html')


def definicoes(request):
    form = DefinicoesForm(user=request.user) if request.user.is_authenticated else None
    return render(request, 'loja/definicoes.html', {'form': form})


@login_required
@require_POST
@transaction.atomic
def atualizar_definicoes(request):
    form = DefinicoesForm(request.POST, user=request.user)
    if not form.is_valid():
        return render(request, 'loja/definicoes.html', {'form': form}, status=400)

    form.save()
    idioma = form.cleaned_data['idioma']
    request.session['mira_idioma'] = idioma
    request.session.modified = True
    messages.success(request, 'As suas definições foram atualizadas.')

    response = redirect('definicoes')
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        idioma,
        max_age=settings.LANGUAGE_COOKIE_AGE,
        path=settings.LANGUAGE_COOKIE_PATH,
        domain=settings.LANGUAGE_COOKIE_DOMAIN,
        secure=settings.LANGUAGE_COOKIE_SECURE,
        httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
        samesite=settings.LANGUAGE_COOKIE_SAMESITE,
    )
    return response


@login_required
@require_POST
@transaction.atomic
def desativar_conta(request):
    if request.user.is_staff:
        messages.error(request, 'Contas administrativas devem ser desativadas pelo responsável pela organização.')
        return redirect('definicoes')

    usuario = request.user
    usuario.is_active = False
    usuario.set_unusable_password()
    usuario.save(update_fields=['is_active', 'password'])
    request.session.flush()
    return redirect('home')


def politica_devolucao(request): return render(request, 'loja/devolucao.html')
def guia(request):
    primeira_abertura = request.session.pop(GUIDE_INTRO_PENDING_SESSION_KEY, False)
    request.session[GUIDE_INTRO_SESSION_KEY] = True
    return render(request, 'loja/guia.html', {'primeira_abertura_guia': primeira_abertura})
