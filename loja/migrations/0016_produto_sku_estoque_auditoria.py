from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def preencher_skus(apps, schema_editor):
    Produto = apps.get_model('loja', 'Produto')
    for produto in Produto.objects.filter(sku__isnull=True).order_by('pk').iterator():
        produto.sku = f'MRC-{produto.pk:08d}'
        produto.save(update_fields=['sku'])


def criar_saldos_iniciais(apps, schema_editor):
    Produto = apps.get_model('loja', 'Produto')
    MovimentacaoEstoque = apps.get_model('loja', 'MovimentacaoEstoque')
    for produto in Produto.objects.filter(quantidade_estoque__gt=0).iterator():
        MovimentacaoEstoque.objects.create(
            produto_id=produto.pk,
            tipo='entrada',
            quantidade=produto.quantidade_estoque,
            saldo_anterior=0,
            saldo_posterior=produto.quantidade_estoque,
            referencia='Migração inicial 0016',
            observacao='Saldo existente antes da ativação do ledger de estoque.',
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('loja', '0015_perfil_idioma'),
    ]

    operations = [
        migrations.AddField(
            model_name='produto',
            name='sku',
            field=models.CharField(blank=True, db_index=True, max_length=32, null=True, unique=True),
        ),
        migrations.RunPython(preencher_skus, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='produto',
            name='sku',
            field=models.CharField(db_index=True, editable=False, max_length=32, unique=True),
        ),
        migrations.CreateModel(
            name='AuditoriaAdministrativa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acao', models.CharField(db_index=True, max_length=30)),
                ('modelo', models.CharField(db_index=True, max_length=100)),
                ('objeto_id', models.CharField(blank=True, max_length=100)),
                ('alteracoes', models.JSONField(blank=True, default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='auditorias_administrativas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-criado_em', '-id'),
                'indexes': [
                    models.Index(fields=['modelo', 'objeto_id'], name='loja_audito_modelo_171f7c_idx'),
                    models.Index(fields=['usuario', 'criado_em'], name='loja_audito_usuario_893585_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='HistoricoStatusPedido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status_anterior', models.CharField(blank=True, max_length=20)),
                ('status_novo', models.CharField(max_length=20)),
                ('observacao', models.CharField(blank=True, max_length=255)),
                ('criado_em', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('pedido', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='historico_status', to='loja.pedido')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='alteracoes_status_pedido', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ('-criado_em', '-id')},
        ),
        migrations.CreateModel(
            name='MovimentacaoEstoque',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('entrada', 'Entrada'), ('venda', 'Venda'), ('ajuste', 'Ajuste'), ('devolucao', 'Devolução'), ('perda', 'Perda')], db_index=True, max_length=20)),
                ('quantidade', models.IntegerField(help_text='Variação do estoque. Entradas são positivas e saídas negativas.')),
                ('saldo_anterior', models.PositiveIntegerField()),
                ('saldo_posterior', models.PositiveIntegerField()),
                ('referencia', models.CharField(blank=True, max_length=120)),
                ('observacao', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('pedido', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='movimentacoes_estoque', to='loja.pedido')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimentacoes_estoque', to='loja.produto')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimentacoes_estoque', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-criado_em', '-id'),
                'indexes': [
                    models.Index(fields=['produto', 'criado_em'], name='loja_movime_produto_aa0bea_idx'),
                    models.Index(fields=['tipo', 'criado_em'], name='loja_movime_tipo_4e4bc1_idx'),
                ],
            },
        ),
        migrations.RunPython(criar_saldos_iniciais, migrations.RunPython.noop),
    ]
