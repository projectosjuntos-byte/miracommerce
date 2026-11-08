from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from .models import Perfil


@transaction.atomic
def anonimizar_usuario(usuario):
    """Remove PII mantendo os registros financeiros necessários para auditoria."""
    identificador = uuid4().hex[:16]
    usuario.username = f'anon-{identificador}'
    usuario.email = f'{identificador}@anon.invalid'
    usuario.first_name = ''
    usuario.last_name = ''
    usuario.is_active = False
    usuario.set_unusable_password()
    usuario.save(update_fields=['username', 'email', 'first_name', 'last_name', 'is_active', 'password'])

    perfil, _ = Perfil.objects.get_or_create(usuario=usuario)
    perfil.telefone = ''
    perfil.provincia = ''
    perfil.municipio = ''
    perfil.bairro = ''
    perfil.saldo_bonus = 0
    perfil.save(update_fields=['telefone', 'provincia', 'municipio', 'bairro', 'saldo_bonus'])
    return usuario


def exportar_dados_usuario(usuario):
    perfil = Perfil.objects.filter(usuario=usuario).values(
        'idioma', 'telefone', 'provincia', 'municipio', 'bairro', 'saldo_bonus', 'total_compras_realizadas'
    ).first()
    pedidos = []
    for pedido in usuario.pedido_set.select_related('pagamento').prefetch_related('itens__produto').order_by('data_criacao'):
        pedidos.append({
            'id': pedido.id,
            'criado_em': pedido.data_criacao.isoformat(),
            'status': pedido.status,
            'subtotal': str(pedido.subtotal),
            'frete': str(pedido.frete),
            'total': str(pedido.total),
            'itens': [
                {
                    'produto': item.produto.nome,
                    'quantidade': item.quantidade,
                    'preco_unitario': str(item.preco_unitario or 0),
                    'subtotal': str(item.subtotal or 0),
                }
                for item in pedido.itens.all()
            ],
        })
    if perfil and perfil.get('saldo_bonus') is not None:
        perfil['saldo_bonus'] = str(perfil['saldo_bonus'])
    return {
        'conta': {
            'username': usuario.username,
            'email': usuario.email,
            'nome': usuario.get_full_name(),
            'criada_em': usuario.date_joined.isoformat(),
        },
        'perfil': perfil or {},
        'pedidos': pedidos,
    }


def anonimizar_usuarios_inativos(dias, agora=None):
    from django.utils import timezone
    from datetime import timedelta

    agora = agora or timezone.now()
    limite = agora - timedelta(days=dias)
    User = get_user_model()
    usuarios = User.objects.filter(is_active=True, is_staff=False).filter(
        Q(last_login__lt=limite) | Q(last_login__isnull=True, date_joined__lt=limite)
    )
    total = 0
    for usuario in usuarios.iterator():
        anonimizar_usuario(usuario)
        total += 1
    return total
