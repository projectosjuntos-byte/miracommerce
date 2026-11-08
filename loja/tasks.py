import logging

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from .models import Produto
from .recomendacoes import _cache_key, gerar_regras_associacao
from .privacy import anonimizar_usuarios_inativos


logger = logging.getLogger(__name__)
RECOMMENDATION_LOCK_KEY = _cache_key('task_lock', 'regras_associacao')


@shared_task(
    bind=True,
    name='loja.atualizar_promocoes',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def atualizar_promocoes_task(self):
    """Atualiza promoções fora do ciclo de requisição HTTP."""
    alterados = 0
    campos = ('em_promocao', 'status_promocao', 'preco_promocional')

    for produto in Produto.objects.all().iterator():
        anterior = tuple(getattr(produto, campo) for campo in campos)
        produto.aplicar_promocao_automatica()
        atual = tuple(getattr(produto, campo) for campo in campos)
        if atual != anterior:
            produto.save(update_fields=campos)
            alterados += 1

    return alterados


@shared_task(
    bind=True,
    name='loja.gerar_regras_associacao',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def gerar_regras_associacao_task(self):
    """Recalcula o modelo de recomendações no worker Celery."""
    try:
        regras = gerar_regras_associacao(
            force_refresh=True,
            allow_compute=True,
            raise_errors=True,
        )
        return len(regras)
    finally:
        cache.delete(RECOMMENDATION_LOCK_KEY)


def enqueue_recommendation_refresh():
    """Agenda uma atualização no máximo uma vez a cada cinco minutos."""
    if not cache.add(RECOMMENDATION_LOCK_KEY, True, timeout=300):
        return None
    try:
        return gerar_regras_associacao_task.delay()
    except Exception:
        cache.delete(RECOMMENDATION_LOCK_KEY)
        logger.exception('Não foi possível agendar a atualização de recomendações.')
        return None


@shared_task(
    bind=True,
    name='loja.anonimizar_usuarios_inativos',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def anonimizar_usuarios_inativos_task(self):
    """Aplica a retenção configurada sem depender de argumentos do Celery Beat."""
    return anonimizar_usuarios_inativos(dias=settings.DATA_RETENTION_DAYS)


@shared_task(
    bind=True,
    name='loja.enviar_email_status_pedido',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def enviar_email_status_pedido_task(self, pedido_id, status_novo, status_anterior=None, site_url=None):
    """Envia notificação por e-mail quando o status do pedido é alterado."""
    from .notificacoes import enviar_email_notificacao_status
    return enviar_email_notificacao_status(
        pedido_id=pedido_id,
        status_novo=status_novo,
        status_anterior=status_anterior,
        site_url=site_url,
    )
