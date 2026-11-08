from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage

from loja.image_utils import gerar_thumbnail_produto
from loja.models import Produto


class Command(BaseCommand):
    help = 'Gera ou atualiza thumbnails para os produtos e limpa registros inconsistentes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regera os thumbnails de todos os produtos com imagem, substituindo os existentes.',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)

        # 1. Limpa thumbnails de produtos que não possuem imagem
        sem_imagem = Produto.objects.filter(imagem='').exclude(thumbnail__isnull=True)
        limpos = 0
        for p in sem_imagem:
            if p.thumbnail and default_storage.exists(p.thumbnail.name):
                try:
                    default_storage.delete(p.thumbnail.name)
                except Exception:
                    pass
            Produto.objects.filter(pk=p.pk).update(thumbnail=None)
            limpos += 1
        if limpos:
            self.stdout.write(self.style.WARNING(f'{limpos} thumbnail(s) órfã(s) removida(s).'))

        # 2. Gera/atualiza thumbnails para produtos com imagem
        qs = Produto.objects.exclude(imagem='')
        if not force:
            qs = qs.filter(thumbnail__isnull=True)

        total = 0
        for produto in qs.iterator():
            gerar_thumbnail_produto(produto)
            if produto.thumbnail:
                Produto.objects.filter(pk=produto.pk).update(thumbnail=produto.thumbnail.name)
                total += 1

        self.stdout.write(self.style.SUCCESS(f'{total} thumbnail(s) processada(s) com sucesso.'))
