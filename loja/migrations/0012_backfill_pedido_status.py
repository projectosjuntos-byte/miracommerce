from django.db import migrations


def marcar_pedidos_finalizados_como_pagos(apps, schema_editor):
    Pedido = apps.get_model('loja', 'Pedido')
    Pedido.objects.filter(finalizado=True).update(status='paid')


def manter_status_atual(apps, schema_editor):
    # Migração deliberadamente irreversível: não é seguro transformar
    # pedidos pagos novamente em pendentes durante um rollback.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('loja', '0011_pedido_idempotency_key_pedido_status_and_more'),
    ]

    operations = [
        migrations.RunPython(
            marcar_pedidos_finalizados_como_pagos,
            manter_status_atual,
        ),
    ]
