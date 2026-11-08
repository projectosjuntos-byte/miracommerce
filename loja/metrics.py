"""Métricas Prometheus leves para monitorar a aplicação e o checkout."""

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest
    PROMETHEUS_AVAILABLE = True
except ModuleNotFoundError:  # Desenvolvimento local sem requirements-dev instalado.
    PROMETHEUS_AVAILABLE = False

    class _NoopMetric:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            return None

        def observe(self, *args, **kwargs):
            return None

        def set(self, *args, **kwargs):
            return None

    def Counter(*args, **kwargs):
        return _NoopMetric()

    def Gauge(*args, **kwargs):
        return _NoopMetric()

    def Histogram(*args, **kwargs):
        return _NoopMetric()


HTTP_REQUESTS = Counter(
    'miracommerce_http_requests_total',
    'Total de requisições HTTP concluídas.',
    ('method', 'route', 'status'),
)
HTTP_LATENCY = Histogram(
    'miracommerce_http_request_duration_seconds',
    'Duração das requisições HTTP.',
    ('method', 'route'),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)
CHECKOUT_LATENCY = Histogram(
    'miracommerce_checkout_duration_seconds',
    'Duração do checkout transacional.',
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)
CHECKOUT_FAILURES = Counter(
    'miracommerce_checkout_failures_total',
    'Falhas do checkout por tipo de exceção.',
    ('exception',),
)
CELERY_TASKS = Counter(
    'miracommerce_celery_tasks_total',
    'Execuções de tarefas Celery.',
    ('task', 'state'),
)
CELERY_TASK_DURATION = Histogram(
    'miracommerce_celery_task_duration_seconds',
    'Duração de tarefas Celery.',
    ('task',),
)
READY = Gauge(
    'miracommerce_readiness',
    'Disponibilidade das dependências principais (1=ok, 0=indisponível).',
)


def metrics_payload():
    if not PROMETHEUS_AVAILABLE:
        return b'# prometheus-client is not installed\n'
    return generate_latest()
