import logging
from urllib.parse import quote
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.db import transaction

from .models import Pedido

logger = logging.getLogger(__name__)

STATUS_METADATA = {
    Pedido.Status.PENDING_PAYMENT: {
        'titulo': 'Pedido Recebido - Aguardando Pagamento',
        'badge_label': 'Aguardando Pagamento',
        'badge_cor': '#D97706',
        'badge_bg': '#FEF3C7',
        'icone': '⏳',
        'mensagem': 'O seu pedido foi registrado com sucesso e está aguardando a confirmação do pagamento para liberação da separação.',
        'proximo_passo': 'Assim que o pagamento for verificado, iniciaremos a preparação dos seus produtos imediatamente.',
    },
    Pedido.Status.PAID: {
        'titulo': 'Pagamento Confirmado com Sucesso',
        'badge_label': 'Pagamento Aprovado',
        'badge_cor': '#0284C7',
        'badge_bg': '#E0F2FE',
        'icone': '💳',
        'mensagem': 'Confirmamos a liquidação do seu pagamento. A nossa equipe do armazém já foi acionada para iniciar a conferência.',
        'proximo_passo': 'Os seus artigos estão sendo separados e conferidos no nosso armazém.',
    },
    Pedido.Status.PROCESSING: {
        'titulo': 'Pedido em Preparação no Armazém',
        'badge_label': 'Em Preparação',
        'badge_cor': '#6366F1',
        'badge_bg': '#EEF2FF',
        'icone': '📦',
        'mensagem': 'Os seus produtos estão em fase de conferência, pesagem e embalagem protegida no nosso centro de distribuição.',
        'proximo_passo': 'O pacote será entregue à transportadora muito em breve para início do transporte.',
    },
    Pedido.Status.SHIPPED: {
        'titulo': 'Pedido Enviado - A Caminho da sua Morada',
        'badge_label': 'Em Transporte',
        'badge_cor': '#EA580C',
        'badge_bg': '#FFEDD5',
        'icone': '🚚',
        'mensagem': 'Excelente notícia! O seu pedido já saiu do armazém e está em rota de transporte para o endereço cadastrado.',
        'proximo_passo': 'Mantenha o seu telefone por perto para contato do estafeta no momento da entrega.',
    },
    Pedido.Status.DELIVERED: {
        'titulo': 'Pedido Entregue com Sucesso!',
        'badge_label': 'Entregue',
        'badge_cor': '#16A34A',
        'badge_bg': '#DCFCE7',
        'icone': '✅',
        'mensagem': 'O seu pedido foi concluído e entregue com sucesso! Esperamos que tenha uma ótima experiência com as suas compras.',
        'proximo_passo': 'Obrigado por escolher a MiraComerce IA. O seu bônus de fidelidade já está ativo na sua conta.',
    },
    Pedido.Status.CANCELLED: {
        'titulo': 'Pedido Cancelado',
        'badge_label': 'Cancelado',
        'badge_cor': '#64748B',
        'badge_bg': '#F1F5F9',
        'icone': '❌',
        'mensagem': 'Informamos que o seu pedido foi cancelado no sistema. Caso já tenha efetuado algum pagamento, o reembolso será processado.',
        'proximo_passo': 'Caso tenha alguma dúvida ou queira reativar o pedido, fale diretamente com a nossa equipe de suporte.',
    },
    Pedido.Status.FAILED: {
        'titulo': 'Falha no Processamento do Pedido',
        'badge_label': 'Falhou',
        'badge_cor': '#DC2626',
        'badge_bg': '#FEE2E2',
        'icone': '⚠️',
        'mensagem': 'Houve uma falha na confirmação ou processamento do seu pedido.',
        'proximo_passo': 'Por favor, tente novamente ou entre em contato com a equipe de apoio ao cliente.',
    },
    Pedido.Status.REFUNDED: {
        'titulo': 'Pedido Reembolsado',
        'badge_label': 'Reembolsado',
        'badge_cor': '#475569',
        'badge_bg': '#F1F5F9',
        'icone': '🔄',
        'mensagem': 'O valor referente a este pedido foi estornado/reembolsado com sucesso.',
        'proximo_passo': 'O comprovativo financeiro encontra-se registrado no sistema.',
    },
}


def obter_metadados_status(status_chave):
    """Retorna metadados visuais e textuais para o status informado."""
    return STATUS_METADATA.get(
        status_chave,
        {
            'titulo': 'Atualização de Pedido',
            'badge_label': str(status_chave).title(),
            'badge_cor': '#64748B',
            'badge_bg': '#F1F5F9',
            'icone': '📦',
            'mensagem': 'O estado do seu pedido foi atualizado pelo sistema.',
            'proximo_passo': 'Consulte o link do pedido para acompanhar a evolução em tempo real.',
        }
    )


def formatar_kz(valor):
    """Formata valor decimal no padrão angolano: 1.234.567,89 Kz"""
    if valor is None:
        valor = Decimal('0.00')
    val_float = float(valor)
    return f"{val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " Kz"


def enviar_email_notificacao_status(pedido_id, status_novo, status_anterior=None, site_url=None):
    """
    Renderiza e envia um e-mail transacional HTML de alto padrão para o cliente
    notificando sobre a mudança de status do pedido.
    """
    try:
        pedido = (
            Pedido.objects
            .select_related('usuario', 'pagamento')
            .prefetch_related('itens__produto')
            .get(id=pedido_id)
        )
    except Pedido.DoesNotExist:
        logger.warning("Tentativa de enviar e-mail para pedido inexistente #%s", pedido_id)
        return False

    destinatario_email = pedido.usuario.email
    if not destinatario_email:
        logger.info(
            "Pedido %s: cliente %s não possui e-mail cadastrado. Notificação por e-mail ignorada.",
            pedido.codigo_pedido,
            pedido.usuario.username,
        )
        return False

    meta = obter_metadados_status(status_novo)
    etapas = pedido.obter_etapas_timeline()
    perfil = getattr(pedido.usuario, 'perfil', None)

    caminho_rastreio = reverse('detalhe_pedido', args=[pedido.id])
    if site_url:
        url_rastreio = f"{site_url.rstrip('/')}{caminho_rastreio}"
    else:
        url_rastreio = f"http://127.0.0.1:8000{caminho_rastreio}"

    contexto = {
        'pedido': pedido,
        'codigo_pedido': pedido.codigo_pedido,
        'status_novo': status_novo,
        'status_anterior': status_anterior,
        'meta': meta,
        'etapas': etapas,
        'perfil': perfil,
        'itens': pedido.itens.all(),
        'url_rastreio': url_rastreio,
        'data_atual': timezone.localtime(timezone.now()).strftime('%d/%m/%Y às %H:%M'),
        'total_formatado': formatar_kz(pedido.total),
        'subtotal_formatado': formatar_kz(pedido.subtotal),
        'frete_formatado': formatar_kz(pedido.frete) if (pedido.frete or 0) > 0 else 'Grátis',
    }

    assunto = f"[MiraComerce IA] {pedido.codigo_pedido} — {meta['titulo']}"

    try:
        html_corpo = render_to_string('loja/emails/status_pedido.html', contexto)
        texto_corpo = render_to_string('loja/emails/status_pedido.txt', contexto)

        mensagem = EmailMultiAlternatives(
            subject=assunto,
            body=texto_corpo,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'MiraComerce IA <nao-responder@miracommerce.ao>'),
            to=[destinatario_email],
        )
        mensagem.attach_alternative(html_corpo, 'text/html')
        mensagem.send(fail_silently=False)

        logger.info(
            "Notificação de status '%s' enviada com sucesso para %s (Pedido %s).",
            status_novo,
            destinatario_email,
            pedido.codigo_pedido,
        )
        return True
    except Exception as exc:
        logger.warning(
            "Não foi possível enviar e-mail de notificação de status para o pedido %s (%s). Verifique as configurações de EMAIL_BACKEND.",
            pedido.codigo_pedido,
            exc,
        )
        return False


def disparar_notificacao_status_pedido(pedido_id, status_novo, status_anterior=None, site_url=None):
    """
    Agenda o envio do e-mail pós-commit do banco de dados, utilizando Celery se disponível
    ou envio síncrono seguro com fallback garantido.
    """
    def _executar():
        try:
            from .tasks import enviar_email_status_pedido_task
            enviar_email_status_pedido_task.delay(pedido_id, status_novo, status_anterior)
        except Exception:
            enviar_email_notificacao_status(pedido_id, status_novo, status_anterior, site_url=site_url)

    transaction.on_commit(_executar)


def gerar_link_whatsapp(telefone, texto_mensagem):
    """Gera link direto para iniciar conversa no WhatsApp com texto codificado."""
    if not telefone:
        return ""
    apenas_digitos = "".join(filter(str.isdigit, str(telefone)))
    if not apenas_digitos:
        return ""
    if len(apenas_digitos) == 9 and apenas_digitos.startswith('9'):
        apenas_digitos = f"244{apenas_digitos}"

    mensagem_codificada = quote(texto_mensagem)
    return f"https://wa.me/{apenas_digitos}?text={mensagem_codificada}"


def gerar_link_whatsapp_cliente(pedido, site_url=None):
    """
    Gera link para o administrador/estafeta notificar o cliente via WhatsApp com 1 clique.
    """
    perfil = getattr(pedido.usuario, 'perfil', None)
    telefone = perfil.telefone if perfil else None
    if not telefone:
        return ""

    meta = obter_metadados_status(pedido.status)
    caminho_rastreio = reverse('detalhe_pedido', args=[pedido.id])
    base_url = (site_url or "http://127.0.0.1:8000").rstrip("/")
    url = f"{base_url}{caminho_rastreio}"

    nome_cliente = pedido.usuario.get_full_name() or pedido.usuario.username
    texto = (
        f"Olá, {nome_cliente}! 👋\n\n"
        f"A sua encomenda *{pedido.codigo_pedido}* na *MiraComerce IA* foi atualizada:\n"
        f"Estado: *{meta['badge_label']}* {meta['icone']}\n\n"
        f"_{meta['mensagem']}_\n\n"
        f"Acompanhe o itinerário e a entrega em tempo real aqui:\n"
        f"{url}\n\n"
        f"Obrigado por comprar conosco!"
    )
    return gerar_link_whatsapp(telefone, texto)


def gerar_link_whatsapp_suporte(pedido, site_url=None):
    """
    Gera link para o cliente falar diretamente com a central de atendimento/suporte
    com a mensagem já pré-preenchida com o código do pedido.
    """
    telefone_suporte = getattr(settings, 'SUPORTE_WHATSAPP_NUMERO', '244923000000')
    caminho_rastreio = reverse('detalhe_pedido', args=[pedido.id])
    base_url = (site_url or "http://127.0.0.1:8000").rstrip("/")
    url = f"{base_url}{caminho_rastreio}"

    texto = (
        f"Olá, suporte MiraComerce IA! 👋\n"
        f"Preciso de auxílio com a minha encomenda *{pedido.codigo_pedido}*.\n"
        f"Link de rastreio: {url}"
    )
    return gerar_link_whatsapp(telefone_suporte, texto)

