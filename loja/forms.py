import logging
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, PasswordResetForm
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import Perfil

logger = logging.getLogger(__name__)

class CadastroForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, label="Primeiro Nome")
    last_name = forms.CharField(max_length=30, required=True, label="Último Nome")
    email = forms.EmailField(required=True, label="Email")
    
    # Campos customizados para a realidade de Angola
    telefone = forms.CharField(max_length=20, required=True, label="Telefone")
    provincia = forms.CharField(max_length=50, required=True, label="Província")
    municipio = forms.CharField(max_length=50, required=True, label="Município")
    bairro = forms.CharField(max_length=50, required=True, label="Bairro")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise forms.ValidationError('Por favor, indique um nome de utilizador.')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Já existe uma conta com este nome de utilizador. Escolha outro.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Já existe uma conta cadastrada com este e-mail.')
        return email

    @transaction.atomic
    def save(self, commit=True):
        # 1. Salva o utilizador base (User)
        user = super().save(commit=False)
        if commit:
            user.save()
            
            # 2. Cria ou Atualiza o Perfil com os dados extras do formulário
            perfil, created = Perfil.objects.get_or_create(usuario=user)
            perfil.telefone = self.cleaned_data.get('telefone')
            perfil.provincia = self.cleaned_data.get('provincia')
            perfil.municipio = self.cleaned_data.get('municipio')
            perfil.bairro = self.cleaned_data.get('bairro')
            # O saldo_bonus começa em 0 por padrão no models.py
            perfil.save()
            
        return user


class DefinicoesForm(forms.Form):
    idioma = forms.ChoiceField(label='Idioma', choices=Perfil.IDIOMA_CHOICES)
    first_name = forms.CharField(label='Primeiro nome', max_length=30, required=True)
    last_name = forms.CharField(label='Último nome', max_length=30, required=True)
    email = forms.EmailField(label='E-mail', required=True)
    telefone = forms.CharField(label='Telefone', max_length=20, required=False)
    provincia = forms.CharField(label='Província', max_length=50, required=False)
    municipio = forms.CharField(label='Município', max_length=50, required=False)
    bairro = forms.CharField(label='Bairro', max_length=50, required=False)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.perfil, _ = Perfil.objects.get_or_create(usuario=user)
        if not self.is_bound:
            self.initial.update({
                'idioma': self.perfil.idioma,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'telefone': self.perfil.telefone or '',
                'provincia': self.perfil.provincia or '',
                'municipio': self.perfil.municipio or '',
                'bairro': self.perfil.bairro or '',
            })
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('Já existe outra conta cadastrada com este e-mail.')
        return email

    @transaction.atomic
    def save(self):
        self.user.first_name = self.cleaned_data['first_name'].strip()
        self.user.last_name = self.cleaned_data['last_name'].strip()
        self.user.email = self.cleaned_data['email']
        self.user.save(update_fields=['first_name', 'last_name', 'email'])

        self.perfil.idioma = self.cleaned_data['idioma']
        self.perfil.telefone = self.cleaned_data['telefone'].strip()
        self.perfil.provincia = self.cleaned_data['provincia'].strip()
        self.perfil.municipio = self.cleaned_data['municipio'].strip()
        self.perfil.bairro = self.cleaned_data['bairro'].strip()
        self.perfil.save(update_fields=['idioma', 'telefone', 'provincia', 'municipio', 'bairro'])
        return self.user


class RecuperarSenhaForm(PasswordResetForm):
    """
    Formulário avançado e resiliente de recuperação de senha.
    Suporta entrada por endereço de e-mail ou nome de utilizador (username).
    Garante despacho com link absoluto HTTPS e templates transacionais HTML/texto.
    """
    email = forms.CharField(
        label='E-mail ou Nome de Utilizador',
        max_length=254,
        widget=forms.TextInput(attrs={
            'autocomplete': 'email',
            'placeholder': 'exemplo@dominio.com ou seu_usuario',
            'class': 'form-control',
            'required': True,
        }),
    )

    def clean_email(self):
        return self.cleaned_data['email'].strip()

    def get_users(self, email):
        """
        Retorna utilizadores ativos que correspondam ao e-mail informado
        ou ao nome de utilizador (username).
        """
        user_model = User
        identificador = email.strip()

        # 1. Busca por e-mail direto
        active_users = user_model._default_manager.filter(
            email__iexact=identificador,
            is_active=True,
        )

        # 2. Se não encontrar por e-mail, busca por username
        if not active_users.exists():
            active_users = user_model._default_manager.filter(
                username__iexact=identificador,
                is_active=True,
            )

        usuarios_validos = []
        for u in active_users:
            if u.has_usable_password() and u.email:
                usuarios_validos.append(u)

        if not usuarios_validos:
            logger.info("Recuperação de senha solicitada, mas nenhum utilizador ativo com senha utilizável foi encontrado para '%s'.", identificador)

        return usuarios_validos

    def save(self, domain_override=None,
             subject_template_name='loja/emails/recuperar_senha_assunto.txt',
             email_template_name='loja/emails/recuperar_senha_email.txt',
             use_https=False, token_generator=None,
             from_email=None, request=None,
             html_email_template_name='loja/emails/recuperar_senha_email.html',
             extra_email_context=None):
        """
        Gera o link de recuperação seguro e despacha o e-mail transacional HTML e texto.
        """
        from django.contrib.auth.tokens import default_token_generator
        if token_generator is None:
            token_generator = default_token_generator

        identificador = self.cleaned_data["email"]

        site_base = getattr(settings, 'SITE_URL', 'https://miracommerce.vercel.app').rstrip('/')
        if request and request.is_secure():
            use_https = True
        elif site_base.startswith('https://'):
            use_https = True

        protocol = 'https' if use_https else 'http'

        if domain_override:
            domain = domain_override
        elif site_base:
            domain = site_base.split('://')[-1]
        elif request:
            domain = request.get_host()
        else:
            domain = 'miracommerce.vercel.app'

        site_name = 'MiraComerce IA'
        from_email = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', None)

        users = list(self.get_users(identificador))
        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)
            reset_url = f"{protocol}://{domain}/reset/{uid}/{token}/"

            context = {
                'email': user.email,
                'user': user,
                'domain': domain,
                'site_name': site_name,
                'site_url': site_base,
                'uid': uid,
                'token': token,
                'protocol': protocol,
                'reset_url': reset_url,
                'ano_atual': timezone.now().year,
                **(extra_email_context or {}),
            }

            self.send_mail(
                subject_template_name,
                email_template_name,
                context,
                from_email,
                user.email,
                html_email_template_name=html_email_template_name,
            )
            logger.info("E-mail de recuperação de senha despachado com sucesso para %s (uid=%s).", user.email, uid)
