import sys
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Testa as configurações de e-mail e envia uma mensagem de teste para o endereço informado."

    def add_arguments(self, parser):
        parser.add_argument(
            'destinatario',
            nargs='?',
            default='',
            help='Endereço de e-mail de destino para o teste (opcional, padrão: EMAIL_HOST_USER)',
        )

    def handle(self, *args, **options):
        destinatario = (options['destinatario'] or getattr(settings, 'EMAIL_HOST_USER', '')).strip()

        self.stdout.write(self.style.MIGRATE_HEADING("=== DIAGNÓSTICO DE E-MAIL — MIRACOMERCE IA ==="))
        self.stdout.write(f"EMAIL_BACKEND:       {settings.EMAIL_BACKEND}")
        self.stdout.write(f"EMAIL_HOST:          {getattr(settings, 'EMAIL_HOST', 'não definido')}")
        self.stdout.write(f"EMAIL_PORT:          {getattr(settings, 'EMAIL_PORT', 'não definido')}")
        self.stdout.write(f"EMAIL_USE_TLS:       {getattr(settings, 'EMAIL_USE_TLS', False)}")
        self.stdout.write(f"EMAIL_USE_SSL:       {getattr(settings, 'EMAIL_USE_SSL', False)}")
        self.stdout.write(f"EMAIL_TIMEOUT:       {getattr(settings, 'EMAIL_TIMEOUT', 10)}s")
        self.stdout.write(f"EMAIL_HOST_USER:     {getattr(settings, 'EMAIL_HOST_USER', 'não definido') or '(vazio)'}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL:  {getattr(settings, 'DEFAULT_FROM_EMAIL', 'não definido')}")
        self.stdout.write(f"SITE_URL:            {getattr(settings, 'SITE_URL', 'não definido')}")
        self.stdout.write("--------------------------------------------------")

        if 'console.EmailBackend' in settings.EMAIL_BACKEND:
            self.stdout.write(self.style.WARNING(
                "ATENÇÃO: O backend atual é 'console.EmailBackend'.\n"
                "Os e-mails NÃO serão enviados pela internet para caixas de entrada reais.\n"
                "Para enviar e-mails reais, configure EMAIL_HOST_USER e EMAIL_HOST_PASSWORD no seu .env ou nas Variáveis de Ambiente da Vercel."
            ))

        if not destinatario or '@' not in destinatario:
            self.stdout.write(self.style.ERROR(
                "Erro: Indique um e-mail de destino válido para realizar o teste.\n"
                "Exemplo: python manage.py test_email seu-email@gmail.com"
            ))
            return

        self.stdout.write(f"Iniciando tentativa de envio de e-mail de teste para: {destinatario}...")

        assunto = f"[MiraComerce IA] Teste de Conexão de E-mail ({timezone.now().strftime('%d/%m/%Y %H:%M')})"
        corpo_texto = (
            f"Olá!\n\n"
            f"Este é um e-mail de teste enviado pela plataforma MiraComerce IA para verificar o funcionamento do servidor SMTP.\n\n"
            f"Se está a ler esta mensagem, a sua configuração de e-mail está 100% OPERACIONAL!\n\n"
            f"Configurações utilizadas:\n"
            f"- Servidor: {getattr(settings, 'EMAIL_HOST', '')}:{getattr(settings, 'EMAIL_PORT', '')}\n"
            f"- Remetente: {getattr(settings, 'DEFAULT_FROM_EMAIL', '')}\n"
            f"- Data/Hora: {timezone.now().strftime('%d/%m/%Y às %H:%M:%S')}\n\n"
            f"Atenciosamente,\n"
            f"MiraComerce IA — Luanda, Angola\n"
        )
        corpo_html = (
            f"<div style='font-family: sans-serif; max-width: 600px; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px;'>"
            f"<h2 style='color: #1a1d1e;'>MiraComerce <span style='color: #e67315;'>IA</span></h2>"
            f"<div style='background-color: #dcfce7; border-left: 4px solid #16a34a; padding: 12px; margin: 16px 0; border-radius: 4px; color: #166534; font-weight: bold;'>"
            f"✔ Configuração de e-mail 100% OPERACIONAL!"
            f"</div>"
            f"<p style='color: #334155; font-size: 14px;'>Este é um e-mail de teste transacional validando o envio a partir da sua infraestrutura.</p>"
            f"<ul style='color: #475569; font-size: 13px;'>"
            f"<li><strong>Servidor:</strong> {getattr(settings, 'EMAIL_HOST', '')}:{getattr(settings, 'EMAIL_PORT', '')}</li>"
            f"<li><strong>Remetente:</strong> {getattr(settings, 'DEFAULT_FROM_EMAIL', '')}</li>"
            f"<li><strong>Destinatário:</strong> {destinatario}</li>"
            f"</ul>"
            f"<p style='color: #94a3b8; font-size: 12px; border-top: 1px solid #e2e8f0; padding-top: 12px; margin-top: 24px;'>"
            f"MiraComerce IA &bull; Luanda, Angola"
            f"</p>"
            f"</div>"
        )

        try:
            conexao = get_connection(fail_silently=False)
            msg = EmailMultiAlternatives(
                subject=assunto,
                body=corpo_texto,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
                to=[destinatario],
                connection=conexao,
            )
            msg.attach_alternative(corpo_html, 'text/html')
            msg.send(fail_silently=False)

            self.stdout.write(self.style.SUCCESS(
                f"\n✔ SUCESSO! E-mail de teste enviado com êxito para {destinatario}."
            ))
        except Exception as exc:
            self.stdout.write(self.style.ERROR(
                f"\n❌ FALHA NO ENVIO DO E-MAIL: {exc}"
            ))
            msg_str = str(exc).lower()

            self.stdout.write(self.style.MIGRATE_HEADING("\n--- GUIA DE RESOLUÇÃO DO PROBLEMA ---"))
            if '535' in msg_str or 'authentication' in msg_str or 'badcredentials' in msg_str:
                self.stdout.write(self.style.WARNING(
                    "Causa provável: Autenticação rejeitada pelo provedor (ex: Gmail).\n"
                    "Como corrigir no Gmail:\n"
                    "1. Aceda à sua Conta Google: https://myaccount.google.com/security\n"
                    "2. Ative a 'Verificação em dois passos'.\n"
                    "3. Aceda a 'Palavras-passe de aplicações': https://myaccount.google.com/apppasswords\n"
                    "4. Crie uma nova palavra-passe (ex: nome 'MiraComerce') e copie o código de 16 letras gerado.\n"
                    "5. Insira esse código de 16 letras na variável EMAIL_HOST_PASSWORD (não use a sua senha normal do Google!)."
                ))
            elif 'timeout' in msg_str or 'timed out' in msg_str:
                self.stdout.write(self.style.WARNING(
                    "Causa provável: Tempo limite esgotado ao contactar o servidor SMTP.\n"
                    "Verifique se a porta (ex: 587 para TLS ou 465 para SSL) está acessível na sua rede/provedor."
                ))
            elif 'connection refused' in msg_str or '10061' in msg_str:
                self.stdout.write(self.style.WARNING(
                    "Causa provável: Conexão recusada pelo host de e-mail.\n"
                    "Verifique se EMAIL_HOST (ex: smtp.gmail.com) e EMAIL_PORT (ex: 587) estão corretos."
                ))
            elif '553' in msg_str or 'sender' in msg_str:
                self.stdout.write(self.style.WARNING(
                    "Causa provável: O endereço DEFAULT_FROM_EMAIL não coincide com EMAIL_HOST_USER.\n"
                    "O Gmail e provedores modernos exigem que o remetente seja idêntico ao e-mail autenticado."
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    "Consulte os detalhes da exceção acima para ajustar as variáveis EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER e EMAIL_HOST_PASSWORD."
                ))
