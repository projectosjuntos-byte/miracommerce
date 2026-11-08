from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import transaction
from .metrics import CHECKOUT_FAILURES, CHECKOUT_LATENCY
from time import perf_counter

from .estoque import registrar_movimentacao_estoque
from .models import ItemPedido, MovimentacaoEstoque, Pagamento, Perfil, Pedido, Produto, Venda


def calcular_bonus_compra(total_venda):
    """Calcula o bônus de 5% sobre a compra."""
    return (Decimal(str(total_venda)) * Decimal('0.05')).quantize(Decimal('0.01'))


def calcular_frete(subtotal):
    if subtotal >= settings.FRETE_GRATIS_MINIMO:
        return Decimal('0.00')
    return settings.FRETE_PADRAO


def carregar_itens_carrinho(carrinho):
    """Constroi a lista de itens do carrinho com preços dinâmicos."""
    itens = []
    total = Decimal('0.00')

    ids = [int(p_id) for p_id in carrinho.keys() if str(p_id).isdigit()]
    if not ids:
        return itens, total

    produtos_map = {produto.id: produto for produto in Produto.objects.filter(id__in=ids)}
    for p_id, qtd in carrinho.items():
        try:
            produto = produtos_map.get(int(p_id))
            if not produto:
                continue
            produto.aplicar_promocao_automatica()
            preco_final = produto.obter_preco_venda()
            subtotal = preco_final * qtd
            total += subtotal
            itens.append({
                'produto': produto,
                'quantidade': qtd,
                'subtotal': subtotal,
                'preco_unitario': preco_final,
            })
        except (TypeError, ValueError, Produto.DoesNotExist):
            continue

    return itens, total


def observe_checkout(func):
    def wrapped(*args, **kwargs):
        started = perf_counter()
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            CHECKOUT_FAILURES.labels(type(exc).__name__).inc()
            raise
        finally:
            CHECKOUT_LATENCY.observe(perf_counter() - started)

    wrapped.__name__ = func.__name__
    wrapped.__doc__ = func.__doc__
    return wrapped


@observe_checkout
@transaction.atomic
def processar_finalizacao_compra(usuario, carrinho, idempotency_key=None):
    """Processa um checkout interno de forma transacional e idempotente."""
    if not carrinho:
        return Decimal('0.00'), Decimal('0.00')

    if not settings.SIMULATED_PAYMENTS_ENABLED:
        raise ValueError(
            'O pagamento ainda não foi confirmado. Configure um provedor de pagamentos para finalizar compras.'
        )

    if idempotency_key is None:
        idempotency_key = uuid4()
    elif not isinstance(idempotency_key, UUID):
        idempotency_key = UUID(str(idempotency_key))

    # Serializa checkouts do mesmo cliente e impede duplo clique/concor­rência.
    usuario = get_user_model().objects.select_for_update().get(pk=usuario.pk)
    pedido_existente = Pedido.objects.filter(idempotency_key=idempotency_key).first()
    if pedido_existente:
        if pedido_existente.usuario_id != usuario.id:
            raise ValueError('A chave de checkout já está vinculada a outro cliente.')
        if pedido_existente.status != Pedido.Status.PAID:
            raise ValueError('Este checkout não está disponível para repetição.')
        return pedido_existente.total, calcular_bonus_compra(pedido_existente.total)

    ids = [int(p_id) for p_id in carrinho.keys() if str(p_id).isdigit()]
    if not ids:
        raise ValueError('Carrinho vazio ou inválido.')

    produtos_map = {
        produto.id: produto for produto in Produto.objects.select_for_update().filter(id__in=ids)
    }

    itens_para_processar = []
    for p_id, qtd in carrinho.items():
        if isinstance(qtd, bool) or not isinstance(qtd, int) or qtd <= 0:
            raise ValueError('Quantidade inválida no carrinho.')

        produto = produtos_map.get(int(p_id))
        if not produto:
            raise ValueError('Produto indisponível no momento.')

        if produto.data_validade and produto.data_validade < date.today():
            raise ValueError(f'{produto.nome} está fora da validade e não pode ser vendido.')

        produto.aplicar_promocao_automatica()
        if produto.quantidade_estoque < qtd:
            raise ValueError(f'Estoque insuficiente para {produto.nome}.')

        preco_venda = produto.obter_preco_venda()
        if preco_venda <= 0:
            raise ValueError(f'{produto.nome} possui um preço inválido.')

        itens_para_processar.append((produto, qtd, preco_venda))

    subtotal_venda = Decimal('0.00')
    vendas_para_criar = []
    itens_pedido_para_criar = []
    produtos_para_atualizar = []

    with transaction.atomic():
        for produto, qtd, preco_venda in itens_para_processar:
            subtotal_venda += preco_venda * qtd

        frete = calcular_frete(subtotal_venda)
        total_venda = subtotal_venda + frete

        pedido = Pedido(
            usuario=usuario,
            subtotal=subtotal_venda,
            frete=frete,
            total=total_venda,
            finalizado=True,
            status=Pedido.Status.PAID,
            idempotency_key=idempotency_key,
        )
        pedido._status_actor_id = usuario.pk
        pedido.save()

        for produto, qtd, preco_venda in itens_para_processar:
            itens_pedido_para_criar.append(ItemPedido(
                pedido=pedido,
                produto=produto,
                quantidade=qtd,
                preco_unitario=preco_venda,
                subtotal=preco_venda * qtd,
            ))

            vendas_para_criar.append(Venda(
                id_transacao=pedido.id,
                usuario=usuario,
                produto=produto,
                pedido=pedido,
                preco_unitario=preco_venda,
                quantidade=qtd,
            ))

            registrar_movimentacao_estoque(
                produto,
                -qtd,
                MovimentacaoEstoque.Tipo.VENDA,
                usuario=usuario,
                pedido=pedido,
                referencia=f'Pedido #{pedido.pk}',
                observacao='Baixa automática após checkout confirmado.',
            )
            produtos_para_atualizar.append(produto)

        if itens_pedido_para_criar:
            ItemPedido.objects.bulk_create(itens_pedido_para_criar)

        if vendas_para_criar:
            Venda.objects.bulk_create(vendas_para_criar)

        if produtos_para_atualizar:
            Produto.objects.bulk_update(
                produtos_para_atualizar,
                ['em_promocao', 'status_promocao', 'preco_promocional']
            )

        Pagamento.objects.create(
            pedido=pedido,
            status=Pagamento.Status.PAID,
            provider='internal',
            idempotency_key=idempotency_key,
            valor=total_venda,
            detalhes={'mode': 'simulated_checkout'},
        )

        perfil, criado = Perfil.objects.get_or_create(usuario=usuario)
        if not criado:
            perfil = Perfil.objects.select_for_update().get(pk=perfil.pk)
        bonus = calcular_bonus_compra(subtotal_venda)
        perfil.adicionar_bonus(bonus)
        perfil.total_compras_realizadas += 1
        perfil.save(update_fields=['saldo_bonus', 'total_compras_realizadas'])

    return total_venda, bonus
