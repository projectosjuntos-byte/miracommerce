from django.db import migrations, models
from django.core.validators import MinValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ('loja', '0016_produto_sku_estoque_auditoria'),
    ]

    operations = [
        migrations.AddField(
            model_name='venda',
            name='quantidade',
            field=models.PositiveIntegerField(
                default=1,
                help_text='Quantidade do produto nesta linha da venda.',
                validators=[MinValueValidator(1)],
            ),
        ),
    ]
