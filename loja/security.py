from functools import wraps
from hashlib import sha256

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse


def get_client_ip(request):
    """Retorna o IP do cliente sem aceitar cabeçalhos forjados por padrão.

    ``TRUST_PROXY_HEADERS`` só deve ser ativado atrás de um proxy que substitui
    X-Real-IP e X-Forwarded-For pelos valores que ele próprio observou.
    """
    remote_addr = request.META.get('REMOTE_ADDR', 'unknown')
    if not getattr(settings, 'TRUST_PROXY_HEADERS', False):
        return remote_addr

    return request.META.get('HTTP_X_REAL_IP', '').strip() or remote_addr


def rate_limit(name, limit, window, subject_field=None):
    """Limit POST attempts by IP and optional username/email."""
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not getattr(settings, 'AUTH_RATE_LIMIT_ENABLED', True) or request.method != 'POST':
                return view(request, *args, **kwargs)

            configured_limit = (
                getattr(settings, limit, limit)
                if isinstance(limit, str)
                else limit
            )
            ip = get_client_ip(request)
            subject = ''
            if subject_field:
                subject = (request.POST.get(subject_field) or '').strip().lower()
            identifiers = [('ip', ip)]
            if subject:
                identifiers.append(('subject', subject))

            cache_keys = []
            for identifier_type, identifier in identifiers:
                raw_key = f'{name}|{identifier_type}|{identifier}'
                digest = sha256(raw_key.encode('utf-8')).hexdigest()
                cache_keys.append(f'miracommerce:rate-limit:{name}:{digest}')

            counts = [cache.get(key, 0) for key in cache_keys]
            if any(count >= configured_limit for count in counts):
                response = HttpResponse(
                    'Muitas tentativas. Tente novamente mais tarde.',
                    status=429,
                )
                response['Retry-After'] = str(window)
                return response

            for key, count in zip(cache_keys, counts):
                try:
                    if count:
                        cache.incr(key)
                    else:
                        cache.add(key, 1, timeout=window)
                except ValueError:
                    cache.set(key, 1, timeout=window)

            return view(request, *args, **kwargs)

        return wrapped
    return decorator
