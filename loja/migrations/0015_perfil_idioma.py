from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('loja', '0014_produto_thumbnail'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfil',
            name='idioma',
            field=models.CharField(
                choices=[('pt-pt', 'Português'), ('en', 'English')],
                default='pt-pt',
                max_length=5,
            ),
        ),
    ]
