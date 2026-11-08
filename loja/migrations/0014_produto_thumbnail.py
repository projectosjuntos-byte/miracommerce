from django.db import migrations, models

from loja.image_utils import thumbnail_upload_path


class Migration(migrations.Migration):
    dependencies = [('loja', '0013_pedido_frete_pedido_subtotal')]

    operations = [
        migrations.AddField(
            model_name='produto',
            name='thumbnail',
            field=models.ImageField(blank=True, editable=False, null=True, upload_to=thumbnail_upload_path),
        ),
    ]
