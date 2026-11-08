import logging

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .metrics import READY

logger = logging.getLogger(__name__)


@require_GET
def live(request):
    return JsonResponse({'status': 'ok'})


@require_GET
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()

        cache_key = 'miracommerce:health:ready'
        cache.set(cache_key, 'ok', timeout=10)
        if cache.get(cache_key) != 'ok':
            raise RuntimeError('cache indisponível')
        cache.delete(cache_key)
        READY.set(1)
    except Exception:
        READY.set(0)
        logger.exception('Readiness check falhou.')
        return JsonResponse({'status': 'unavailable'}, status=503)

    return JsonResponse({'status': 'ok'})
