from decimal import Decimal

from django.db import migrations, models


def copiar_total_para_subtotal(apps, schema_editor):
    Pedido = apps.get_model('loja', 'Pedido')
    Pedido.objects.filter(subtotal=Decimal('0.00')).exclude(
        total=Decimal('0.00')
    ).update(subtotal=models.F('total'))


class Migration(migrations.Migration):

    dependencies = [
        ('loja', '0012_backfill_pedido_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedido',
            name='frete',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=12,
            ),
        ),
        migrations.AddField(
            model_name='pedido',
            name='subtotal',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=12,
            ),
        ),
        migrations.RunPython(copiar_total_para_subtotal, migrations.RunPython.noop),
    ]
