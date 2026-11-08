import json
import logging
from time import perf_counter
from uuid import uuid4

from .metrics import CELERY_TASKS, CELERY_TASK_DURATION, HTTP_LATENCY, HTTP_REQUESTS


class JsonFormatter(logging.Formatter):
    """Emite logs próprios para agregadores sem vazar dados pessoais."""

    def format(self, record):
        payload = {
            'timestamp': self.formatTime(record, datefmt='%Y-%m-%dT%H:%M:%S%z'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        for key in ('request_id', 'method', 'route', 'status_code', 'duration_ms', 'task_name'):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class RequestIDMiddleware:
    """Adds a server-generated correlation ID to every response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.headers.get('X-Request-ID', '')[:64] or uuid4().hex
        started_at = perf_counter()
        try:
            response = self.get_response(request)
        except Exception:
            duration = perf_counter() - started_at
            logging.getLogger('django.request').exception(
                'Unhandled request error',
                extra={
                    'request_id': request.request_id,
                    'method': request.method,
                    'route': request.path,
                    'status_code': 500,
                    'duration_ms': round(duration * 1000, 2),
                },
            )
            raise
        duration = perf_counter() - started_at
        route = getattr(getattr(request, 'resolver_match', None), 'route', None) or request.path
        HTTP_REQUESTS.labels(request.method, route, str(response.status_code)).inc()
        HTTP_LATENCY.labels(request.method, route).observe(duration)
        logging.getLogger('django.request').info(
            'Request completed',
            extra={
                'request_id': request.request_id,
                'method': request.method,
                'route': route,
                'status_code': response.status_code,
                'duration_ms': round(duration * 1000, 2),
            },
        )
        response['X-Request-ID'] = request.request_id
        response['X-Response-Time-ms'] = f'{duration * 1000:.2f}'
        return response


def register_celery_observability():
    """Registra sinais Celery uma única vez quando o app Django inicializa."""
    from celery.signals import task_failure, task_postrun, task_prerun

    timings = {}

    def on_prerun(task_id=None, task=None, **kwargs):
        timings[task_id] = perf_counter()

    def on_postrun(task_id=None, task=None, state=None, **kwargs):
        task_name = getattr(task, 'name', 'unknown')
        CELERY_TASKS.labels(task_name, state or 'unknown').inc()
        started = timings.pop(task_id, None)
        if started is not None:
            CELERY_TASK_DURATION.labels(task_name).observe(perf_counter() - started)

    def on_failure(task_id=None, task=None, **kwargs):
        CELERY_TASKS.labels(getattr(task, 'name', 'unknown'), 'failure').inc()

    task_prerun.connect(on_prerun, dispatch_uid='miracommerce-observability-prerun')
    task_postrun.connect(on_postrun, dispatch_uid='miracommerce-observability-postrun')
    task_failure.connect(on_failure, dispatch_uid='miracommerce-observability-failure')
