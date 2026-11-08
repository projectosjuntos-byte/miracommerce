from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.core.files.storage import default_storage

from .image_utils import gerar_thumbnail_produto
from .models import HistoricoStatusPedido, Pedido, Produto
from .notificacoes import disparar_notificacao_status_pedido


@receiver(pre_save, sender=Produto)
def capturar_imagem_anterior_produto(sender, instance, **kwargs):
    if not instance.pk:
        instance._imagem_anterior = None
        instance._thumbnail_anterior = None
        return
    antigo = sender.objects.filter(pk=instance.pk).values('imagem', 'thumbnail').first()
    if antigo:
        instance._imagem_anterior = antigo.get('imagem') or ''
        instance._thumbnail_anterior = antigo.get('thumbnail') or ''
    else:
        instance._imagem_anterior = None
        instance._thumbnail_anterior = None


@receiver(post_save, sender=Produto)
def sincronizar_thumbnail_produto(sender, instance, **kwargs):
    """
    Mantém o thumbnail do produto perfeitamente sincronizado com a imagem principal.
    Atualiza o thumbnail sempre que uma nova foto é enviada e limpa caso seja removida.
    """
    imagem_atual = instance.imagem.name if instance.imagem else ''
    thumbnail_atual = instance.thumbnail.name if instance.thumbnail else ''
    imagem_anterior = getattr(instance, '_imagem_anterior', None)
    thumbnail_anterior = getattr(instance, '_thumbnail_anterior', None)

    # Caso 1: A imagem foi removida / desmarcada no formulário
    if not imagem_atual:
        if thumbnail_atual or thumbnail_anterior:
            alvo = thumbnail_atual or thumbnail_anterior
            if alvo and default_storage.exists(alvo):
                try:
                    default_storage.delete(alvo)
                except Exception:
                    pass
            sender.objects.filter(pk=instance.pk).update(thumbnail=None)
            instance.thumbnail = None
        return

    # Caso 2: Novo produto, imagem alterada ou thumbnail em falta
    imagem_mudou = (imagem_anterior is not None and imagem_atual != imagem_anterior)
    sem_thumbnail = not thumbnail_atual

    if imagem_mudou or sem_thumbnail:
        # Se a imagem foi trocada, remove o thumbnail antigo do disco
        if imagem_mudou and thumbnail_anterior and default_storage.exists(thumbnail_anterior):
            try:
                default_storage.delete(thumbnail_anterior)
            except Exception:
                pass

        gerar_thumbnail_produto(instance)
        novo_thumbnail = instance.thumbnail.name if instance.thumbnail else None
        sender.objects.filter(pk=instance.pk).update(thumbnail=novo_thumbnail)


@receiver(post_delete, sender=Produto)
def remover_arquivos_produto_deletado(sender, instance, **kwargs):
    """Remove os arquivos de mídia quando um produto é excluído permanentemente."""
    for campo in (instance.imagem, instance.thumbnail):
        if campo and campo.name:
            try:
                if default_storage.exists(campo.name):
                    default_storage.delete(campo.name)
            except Exception:
                pass


@receiver(pre_save, sender=Pedido)
def capturar_status_anterior_pedido(sender, instance, **kwargs):
    if not instance.pk:
        instance._status_anterior = ''
        return
    instance._status_anterior = sender.objects.filter(pk=instance.pk).values_list('status', flat=True).first() or ''


@receiver(post_save, sender=Pedido)
def registrar_historico_status_pedido(sender, instance, created, **kwargs):
    anterior = getattr(instance, '_status_anterior', '')
    if created or anterior != instance.status:
        HistoricoStatusPedido.objects.create(
            pedido=instance,
            status_anterior=anterior,
            status_novo=instance.status,
            usuario_id=getattr(instance, '_status_actor_id', None),
            observacao='Status inicial do pedido.' if created else 'Status atualizado.',
        )
        disparar_notificacao_status_pedido(instance.id, instance.status, anterior)
