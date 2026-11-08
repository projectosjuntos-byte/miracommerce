from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_GET

from .metrics import metrics_payload


@require_GET
def metrics(request):
    expected_token = getattr(settings, 'METRICS_TOKEN', '')
    supplied_token = request.headers.get('X-Metrics-Token', '')
    if expected_token and supplied_token != expected_token:
        return HttpResponse('forbidden', status=403)
    if not settings.DEBUG and not expected_token and not request.user.is_staff:
        return HttpResponse('forbidden', status=403)
    return HttpResponse(metrics_payload(), content_type='text/plain; version=0.0.4; charset=utf-8')
