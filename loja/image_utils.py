from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def thumbnail_upload_path(instance, filename):
    return f'produtos/thumbnails/{Path(filename).stem}.jpg'


def gerar_thumbnail_produto(produto):
    if not produto.imagem:
        return
    with Image.open(produto.imagem) as imagem:
        imagem = ImageOps.exif_transpose(imagem).convert('RGB')
        imagem.thumbnail((400, 400), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        imagem.save(buffer, format='JPEG', quality=82, optimize=True, progressive=True)
    nome = f'produtos/thumbnails/{Path(produto.imagem.name).stem}.jpg'
    produto.thumbnail.save(nome, ContentFile(buffer.getvalue()), save=False)
