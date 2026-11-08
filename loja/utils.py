import logging

from .services import RecomendacaoService


logger = logging.getLogger(__name__)


def gerar_recomendacoes_apriori(itens_no_carrinho=None):
    """Compatibilidade legada usando o único motor de recomendações atual."""
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
