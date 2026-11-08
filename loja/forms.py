from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from .models import Perfil  # Importante importar o teu modelo Perfil

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
