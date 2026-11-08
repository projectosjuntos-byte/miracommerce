from django.conf import settings
from django.utils import translation
from secrets import token_urlsafe
from urllib.parse import urlparse

from .i18n import translate_html


class SecurityHeadersMiddleware:
    """Aplica cabeçalhos de segurança mesmo quando o SimpleUI altera o MIDDLEWARE."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = token_urlsafe(24)
        response = self.get_response(request)

        if not settings.DEBUG:
            response.setdefault('X-Frame-Options', getattr(settings, 'X_FRAME_OPTIONS', 'DENY'))
            response.setdefault('X-Content-Type-Options', 'nosniff')
            response.setdefault(
                'Referrer-Policy',
                getattr(settings, 'SECURE_REFERRER_POLICY', 'strict-origin-when-cross-origin'),
            )
            media_origin = ''
            media_url = getattr(settings, 'MEDIA_URL', '')
            if media_url.startswith('http'):
                parsed = urlparse(media_url)
                media_origin = f' {parsed.scheme}://{parsed.netloc}'
            style_attributes = "'unsafe-inline'" if getattr(settings, 'CSP_ALLOW_INLINE_STYLE_ATTRIBUTES', False) else "'none'"
            policy = (
                "default-src 'self'; "
                "base-uri 'self'; "
                "object-src 'none'; "
                "frame-ancestors 'self'; "
                f"script-src 'self' 'nonce-{request.csp_nonce}'; "
                f"style-src 'self' 'nonce-{request.csp_nonce}'; "
                f"style-src-attr {style_attributes}; "
                "font-src 'self' data:; "
                f"img-src 'self' data: blob:{media_origin}; "
                f"connect-src 'self'{media_origin}; "
                "form-action 'self'; "
                "frame-src 'self'"
            )
            if getattr(settings, 'CSP_REPORT_URI', ''):
                policy += f"; report-uri {settings.CSP_REPORT_URI}"
            header_name = 'Content-Security-Policy' if getattr(settings, 'CSP_ENFORCE', True) else 'Content-Security-Policy-Report-Only'
            response.setdefault(header_name, policy)

        return response


class UserLanguageMiddleware:
    """Aplica a preferência persistida do utilizador quando não há cookie de idioma."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language_cookie = settings.LANGUAGE_COOKIE_NAME
        language = request.COOKIES.get(language_cookie)
        if request.user.is_authenticated and not language:
            from .models import Perfil

            language = Perfil.objects.filter(usuario_id=request.user.id).values_list('idioma', flat=True).first()
            if language:
                translation.activate(language)
                request.LANGUAGE_CODE = language

        response = self.get_response(request)
        if (
            request.user.is_authenticated
            and language
            and not request.COOKIES.get(language_cookie)
            and language_cookie not in response.cookies
        ):
            response.set_cookie(
                language_cookie,
                language,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )
        return response


class LanguageContentMiddleware:
    """Traduz o texto estático da interface depois de o template ser renderizado."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get('Content-Type', '')
        language = getattr(request, 'LANGUAGE_CODE', translation.get_language())
        if response.status_code == 200 and content_type.startswith('text/html') and language.startswith('en'):
            response.content = translate_html(response.content.decode(response.charset), language).encode(response.charset)
            response.headers.pop('Content-Length', None)
        return response
