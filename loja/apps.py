from django.apps import AppConfig


class LojaConfig(AppConfig):
    name = 'loja'

    def ready(self):
        # O SimpleUI remove este middleware no seu próprio AppConfig. Reponha-o
        # depois de as apps carregarem para aplicar X-Frame-Options de facto e
        # manter o ``security.W002`` ativo no check --deploy.
        from django.conf import settings

        x_frame_middleware = 'django.middleware.clickjacking.XFrameOptionsMiddleware'
        if x_frame_middleware not in settings.MIDDLEWARE:
            settings.MIDDLEWARE.append(x_frame_middleware)

        from . import signals  # noqa: F401
        from .observability import register_celery_observability

        register_celery_observability()
