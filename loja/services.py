"""Fachada de serviços da aplicação.

As views dependem desta camada por domínio. Os módulos antigos continuam
exportando funções compatíveis, mas novas regras devem entrar aqui ou nos
módulos de domínio chamados por estes serviços.
"""

import logging

from .checkout import calcular_frete, carregar_itens_carrinho, processar_finalizacao_compra
from .promocoes import aplicar_promocoes_em_lote, calcular_preco_venda
from .recomendacoes import gerar_regras_associacao, gerar_sugestoes_para_carrinho, obter_recomendacoes_para_produto
from .relatorios import (
    calcular_resumo_vendas,
    consolidar_vendas,
    filtrar_vendas,
    gerar_csv_relatorio_vendas,
    gerar_excel_relatorio_vendas,
    gerar_pdf_relatorio_vendas,
)


logger = logging.getLogger(__name__)


class CatalogoService:
    """Consultas e regras do catálogo."""

    @staticmethod
    def preco_de_venda(produto):
        return calcular_preco_venda(produto)

    @staticmethod
    def aplicar_promocoes(produtos=None):
        return aplicar_promocoes_em_lote(produtos)


class CarrinhoService:
    """Leitura do carrinho e composição do resumo exibido ao cliente."""

    @staticmethod
    def carregar(carrinho):
        itens, subtotal = carregar_itens_carrinho(carrinho)
        frete = calcular_frete(subtotal)
        return {
            'itens': itens,
            'subtotal': subtotal,
            'frete': frete,
            'total': subtotal + frete,
        }


class PedidoService:
    """Orquestração de pedidos, sem depender da camada HTTP."""

    @staticmethod
    def finalizar(usuario, carrinho, idempotency_key=None):
        return processar_finalizacao_compra(usuario, carrinho, idempotency_key=idempotency_key)


class PagamentoService:
    """Ponto de entrada para o pagamento atual e futuros gateways."""

    @staticmethod
    def confirmar_pedido(usuario, carrinho, idempotency_key=None):
        return PedidoService.finalizar(usuario, carrinho, idempotency_key=idempotency_key)


class RecomendacaoService:
    """Serviço único para recomendações por produto, regras e carrinho."""

    regras = staticmethod(gerar_regras_associacao)
    para_produto = staticmethod(obter_recomendacoes_para_produto)
    para_carrinho = staticmethod(gerar_sugestoes_para_carrinho)


class RelatorioService:
    """Consultas e exportações de vendas."""

    filtrar_vendas = staticmethod(filtrar_vendas)
    calcular_resumo = staticmethod(calcular_resumo_vendas)
    consolidar_vendas = staticmethod(consolidar_vendas)
    gerar_csv = staticmethod(gerar_csv_relatorio_vendas)
    gerar_excel = staticmethod(gerar_excel_relatorio_vendas)
    gerar_pdf = staticmethod(gerar_pdf_relatorio_vendas)


def gerar_recomendacoes_apriori(itens_no_carrinho=None):
    """Compatibilidade legada concentrada na fachada de serviços."""
    logger.warning('gerar_recomendacoes_apriori está depreciada; use RecomendacaoService.')
    sugestoes = RecomendacaoService.para_carrinho(itens_no_carrinho or [], limite=3)
    return [
        {
            'id': item['produto_sugerido'].id,
            'base': item['produto_base'].nome,
            'sugestao': item['produto_sugerido'].nome,
            'preco': item['produto_sugerido'].obter_preco_venda(),
            'imagem': item['produto_sugerido'].imagem,
            'confianca': item['confianca'],
        }
        for item in sugestoes
    ]

__all__ = [
    "aplicar_promocoes_em_lote",
    "calcular_preco_venda",
    "carregar_itens_carrinho",
    "processar_finalizacao_compra",
    "gerar_regras_associacao",
    "obter_recomendacoes_para_produto",
    "gerar_sugestoes_para_carrinho",
    "gerar_pdf_relatorio_vendas",
    "filtrar_vendas",
    "gerar_csv_relatorio_vendas",
    "gerar_excel_relatorio_vendas",
    "CatalogoService",
    "CarrinhoService",
    "PedidoService",
    "PagamentoService",
    "RecomendacaoService",
    "RelatorioService",
    "gerar_recomendacoes_apriori",
]
