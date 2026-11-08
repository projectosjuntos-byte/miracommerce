from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class UsernameOrEmailBackend(ModelBackend):
    """Autentica contas pelo nome de utilizador ou pelo e-mail associado."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        user_model = get_user_model()
        identifier = username or kwargs.get(user_model.USERNAME_FIELD)

        if not identifier or password is None:
            return None

        # Dá prioridade ao e-mail quando o valor informado tem formato de e-mail.
        # O cadastro já impede e-mails duplicados; se houver dados legados em
        # duplicidade, o acesso por e-mail é recusado para não escolher uma conta
        # arbitrariamente.
        user = None
        if '@' in identifier:
            email_matches = user_model._default_manager.filter(email__iexact=identifier)
            if email_matches.count() == 1:
                user = email_matches.first()
            elif email_matches.exists():
                user_model().set_password(password)
                return None

        if user is None:
            try:
                user = user_model._default_manager.get_by_natural_key(identifier)
            except user_model.DoesNotExist:
                # Mantém um custo de processamento comparável quando a conta não
                # existe, reduzindo a possibilidade de enumeração de utilizadores.
                user_model().set_password(password)
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
