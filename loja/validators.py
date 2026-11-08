from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_IMAGE_WIDTH = 4000
MAX_IMAGE_HEIGHT = 4000
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}


def validate_product_image(uploaded_file):
    """Validate image content, dimensions and size before it is stored."""
    if not uploaded_file:
        return

    if uploaded_file.size > MAX_IMAGE_SIZE:
        raise ValidationError('A imagem não pode ultrapassar 5 MB.')

    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as image:
            image.verify()

        uploaded_file.seek(0)
        with Image.open(uploaded_file) as image:
            if image.format not in ALLOWED_IMAGE_FORMATS:
                raise ValidationError('Formato de imagem não permitido. Use JPEG, PNG ou WEBP.')
            if image.width > MAX_IMAGE_WIDTH or image.height > MAX_IMAGE_HEIGHT:
                raise ValidationError('A imagem não pode ultrapassar 4000x4000 pixels.')
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError('O arquivo enviado não é uma imagem válida.') from exc
    finally:
        uploaded_file.seek(0)
