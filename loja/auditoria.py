"""Ferramentas para registrar ações administrativas no Django Admin."""

from datetime import date, datetime
from decimal import Decimal

from .models import AuditoriaAdministrativa
from .security import get_client_ip


def _serializar(valor):
    if isinstance(valor, (date, datetime, Decimal)):
        return str(valor)
    if hasattr(valor, 'name'):
        return str(valor.name)
    return valor


def snapshot_modelo(obj):
    """Retorna somente campos concretos em formato seguro para JSON."""
    valores = {}
    for campo in obj._meta.concrete_fields:
        nome = campo.attname
        valores[nome] = _serializar(getattr(obj, nome, None))
    return valores


def registrar_auditoria(request, *, acao, objeto, alteracoes=None):
    meta = getattr(request, 'META', {})
    return AuditoriaAdministrativa.objects.create(
        usuario=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
        acao=acao,
        modelo=objeto._meta.label,
        objeto_id=str(objeto.pk or ''),
        alteracoes=alteracoes or {},
        ip_address=get_client_ip(request) or None,
        user_agent=meta.get('HTTP_USER_AGENT', '')[:1000],
    )
