from decimal import Decimal
from datetime import date, timedelta

from .models import Produto


def aplicar_promocoes_em_lote(produtos):
    """Aplica a promoção automática para uma lista ou queryset de produtos."""
    for produto in produtos:
        produto.aplicar_promocao_automatica()
        produto.save(update_fields=['em_promocao', 'status_promocao', 'preco_promocional'])
    return produtos


def calcular_preco_venda(produto):
    """Retorna o preço de venda final com promoção aplicada."""
    produto.aplicar_promocao_automatica()
    return produto.obter_preco_venda()


def produtos_proximos_do_vencimento(produtos, dias_para_expirar=90):
    """Filtra produtos próximos da validade para alertas de promoção."""
    hoje = date.today()
    limite_validade = hoje + timedelta(days=dias_para_expirar)
    return produtos.filter(data_validade__range=[hoje, limite_validade]).order_by('data_validade')[:5]
