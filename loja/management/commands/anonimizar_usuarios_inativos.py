from django.core.management.base import BaseCommand
from django.conf import settings

from loja.privacy import anonimizar_usuarios_inativos


class Command(BaseCommand):
    help = 'Anonimiza contas não administrativas sem acesso pelo período definido.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=getattr(settings, 'DATA_RETENTION_DAYS', 1825),
            help='Número de dias sem login antes da anonimização.',
        )

    def handle(self, *args, **options):
        total = anonimizar_usuarios_inativos(options['dias'])
        self.stdout.write(self.style.SUCCESS(f'{total} conta(s) anonimizada(s).'))
