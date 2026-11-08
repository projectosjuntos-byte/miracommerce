"""Operações transacionais de estoque e trilha de movimentações."""

from django.db import transaction

from .models import MovimentacaoEstoque, Produto


@transaction.atomic
def registrar_movimentacao_estoque(
    produto,
    quantidade,
    tipo,
    *,
    usuario=None,
    pedido=None,
    referencia='',
    observacao='',
):
    """Aplica uma variação de estoque e registra o saldo antes e depois.

    ``quantidade`` é um delta: entradas e devoluções são positivas, enquanto
    vendas, perdas e ajustes de saída são negativas.
    """
    produto_id = produto.pk if isinstance(produto, Produto) else produto
    produto_bloqueado = Produto.objects.select_for_update().get(pk=produto_id)
    delta = int(quantidade)
    saldo_anterior = produto_bloqueado.quantidade_estoque
    saldo_posterior = saldo_anterior + delta

    if saldo_posterior < 0:
        raise ValueError(f'Estoque insuficiente para {produto_bloqueado.nome}.')

    produto_bloqueado.quantidade_estoque = saldo_posterior
    produto_bloqueado.save(update_fields=['quantidade_estoque'])

    # Mantém a instância recebida coerente para quem continua o mesmo fluxo.
    if isinstance(produto, Produto):
        produto.quantidade_estoque = saldo_posterior

    return MovimentacaoEstoque.objects.create(
        produto=produto_bloqueado,
        tipo=tipo,
        quantidade=delta,
        saldo_anterior=saldo_anterior,
        saldo_posterior=saldo_posterior,
        pedido=pedido,
        usuario=usuario,
        referencia=referencia,
        observacao=observacao,
    )
