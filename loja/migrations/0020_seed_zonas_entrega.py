from decimal import Decimal
from django.db import migrations


def criar_zonas_iniciais(apps, schema_editor):
    ZonaEntrega = apps.get_model('loja', 'ZonaEntrega')

    zonas = [
        {
            'nome': 'Zona 1 - Periferia e Extensão (Cacuaco, Viana, Belas)',
            'taxa': Decimal('4000.00'),
            'descricao': 'Cacuaco, Viana, Zango, Kilamba, Camama, Sequele e arredores',
            'prazo_estimado': 'No mesmo dia ou até 24h',
            'ativo': True,
            'ordem': 1,
        },
        {
            'nome': 'Zona 2 - Intermediária (Talatona, Benfica, Morro Bento)',
            'taxa': Decimal('2500.00'),
            'descricao': 'Talatona, Benfica, Morro Bento, Kilamba Kiaxi, Golfe e Samba',
            'prazo_estimado': 'Em até 12h',
            'ativo': True,
            'ordem': 2,
        },
        {
            'nome': 'Zona 3 - Centro Urbano (Luanda Central)',
            'taxa': Decimal('1500.00'),
            'descricao': 'Maianga, Ingombota, Alvalade, Miramar, Maculusso, Cruzeiro e Mutamba',
            'prazo_estimado': 'Em até 4h a 6h',
            'ativo': True,
            'ordem': 3,
        },
    ]

    for dados in zonas:
        ZonaEntrega.objects.get_or_create(
            nome=dados['nome'],
            defaults=dados,
        )


def reverter_zonas(apps, schema_editor):
    ZonaEntrega = apps.get_model('loja', 'ZonaEntrega')
    ZonaEntrega.objects.filter(
        nome__in=[
            'Zona 1 - Periferia e Extensão (Cacuaco, Viana, Belas)',
            'Zona 2 - Intermediária (Talatona, Benfica, Morro Bento)',
            'Zona 3 - Centro Urbano (Luanda Central)',
        ]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('loja', '0019_zonaentrega_pedido_endereco_entrega_and_more'),
    ]

    operations = [
        migrations.RunPython(criar_zonas_iniciais, reverter_zonas),
    ]
