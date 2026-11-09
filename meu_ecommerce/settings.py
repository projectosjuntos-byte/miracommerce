import os
import sys
from pathlib import Path
from decimal import Decimal

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env', override=True)

def _env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ('1', 'true', 'yes', 'on')


DEBUG = _env_bool('DEBUG', False)
TESTING = 'test' in sys.argv
IS_COLLECTSTATIC = 'collectstatic' in sys.argv
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG or TESTING or IS_COLLECTSTATIC or _env_bool('VERCEL', False):
        SECRET_KEY = 'mira-commerce-production-fallback-key-7a9f8b2c1d3e4f5a6b7c8d9e0f1a2b3c4d5e'
    else:
        raise ImproperlyConfigured('SECRET_KEY deve ser definida em produção.')

if not DEBUG and not TESTING and not IS_COLLECTSTATIC:
    if SECRET_KEY.lower().startswith('troque-') or len(SECRET_KEY) < 32:
        raise ImproperlyConfigured('SECRET_KEY de produção deve ser longa e aleatória (mínimo 32 caracteres).')

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        'ALLOWED_HOSTS',
        '*' if _env_bool('VERCEL', False) else ('localhost,127.0.0.1,testserver,.vercel.app' if DEBUG else '.vercel.app'),
    ).split(',')
    if host.strip()
]
# Garante suporte automático à Vercel e ambientes locais
if '.vercel.app' not in ALLOWED_HOSTS and '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('.vercel.app')
if _env_bool('VERCEL', False) and '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('*')
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured('ALLOWED_HOSTS deve conter pelo menos um host em produção.')

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]
if 'https://*.vercel.app' not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append('https://*.vercel.app')
vercel_url = os.environ.get('VERCEL_URL')
if vercel_url:
    https_vercel = f'https://{vercel_url}'
    if https_vercel not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(https_vercel)

CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', '900'))
RECOMENDACAO_CACHE_TIMEOUT = int(os.environ.get('RECOMENDACAO_CACHE_TIMEOUT', '3600'))
CATALOG_PAGE_SIZE = int(os.environ.get('CATALOG_PAGE_SIZE', '24'))
RECOMMENDATION_LOOKBACK_DAYS = int(os.environ.get('RECOMMENDATION_LOOKBACK_DAYS', '365'))
RECOMMENDATION_MAX_TRANSACTIONS = int(os.environ.get('RECOMMENDATION_MAX_TRANSACTIONS', '20000'))
RECOMMENDATION_MAX_ITEMS_PER_TRANSACTION = int(os.environ.get('RECOMMENDATION_MAX_ITEMS_PER_TRANSACTION', '50'))
RECOMMENDATION_MIN_SUPPORT = float(os.environ.get('RECOMMENDATION_MIN_SUPPORT', '0.01'))
RECOMMENDATION_MIN_LIFT = float(os.environ.get('RECOMMENDATION_MIN_LIFT', '1.0'))
RECOMMENDATION_MAX_RULES = int(os.environ.get('RECOMMENDATION_MAX_RULES', '500'))
ENABLE_SECURE_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', not DEBUG)
FRETE_GRATIS_MINIMO = Decimal(os.environ.get('FRETE_GRATIS_MINIMO', '25000.00'))
FRETE_PADRAO = Decimal(os.environ.get('FRETE_PADRAO', '0.00'))
AUTH_RATE_LIMIT_ENABLED = _env_bool('AUTH_RATE_LIMIT_ENABLED', True)
AUTH_LOGIN_RATE_LIMIT = int(os.environ.get('AUTH_LOGIN_RATE_LIMIT', '10'))
AUTH_PASSWORD_RESET_RATE_LIMIT = int(os.environ.get('AUTH_PASSWORD_RESET_RATE_LIMIT', '5'))
DATA_RETENTION_DAYS = int(os.environ.get('DATA_RETENTION_DAYS', '1825'))
SIMULATED_PAYMENTS_ENABLED = _env_bool('SIMULATED_PAYMENTS_ENABLED', DEBUG)
REDIS_URL = os.environ.get('REDIS_URL', '').strip()
if _env_bool('VERCEL', False) or not REDIS_URL:
    USE_REDIS_CACHE = _env_bool('USE_REDIS_CACHE', False)
    if not REDIS_URL:
        REDIS_URL = 'redis://127.0.0.1:6379/1'
else:
    USE_REDIS_CACHE = _env_bool('USE_REDIS_CACHE', not DEBUG)
METRICS_TOKEN = os.environ.get('METRICS_TOKEN', '').strip()
TRUST_PROXY_HEADERS = _env_bool('TRUST_PROXY_HEADERS', _env_bool('VERCEL', False))

INSTALLED_APPS = [
    'simpleui',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'loja',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'loja.observability.RequestIDMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'loja.middleware.UserLanguageMiddleware',
    'loja.middleware.LanguageContentMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'loja.middleware.SecurityHeadersMiddleware',
]

ROOT_URLCONF = 'meu_ecommerce.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'loja.views.carrinho_global',
            ],
        },
    },
]

WSGI_APPLICATION = 'meu_ecommerce.wsgi.application'

DB_ENGINE = os.environ.get('DB_ENGINE', 'django.db.backends.mysql')
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    try:
        import dj_database_url
        DATABASES = {
            'default': dj_database_url.parse(
                DATABASE_URL,
                conn_max_age=int(os.environ.get('DB_CONN_MAX_AGE', '60')),
            )
        }
    except ImportError:
        from urllib.parse import parse_qs, urlparse
        u = urlparse(DATABASE_URL)
        engine_map = {
            'postgres': 'django.db.backends.postgresql',
            'postgresql': 'django.db.backends.postgresql',
            'mysql': 'django.db.backends.mysql',
            'sqlite': 'django.db.backends.sqlite3',
        }
        engine = engine_map.get(u.scheme, 'django.db.backends.mysql')
        db_name = u.path.lstrip('/').split('?')[0]
        DATABASES = {
            'default': {
                'ENGINE': engine,
                'NAME': db_name,
                'USER': u.username or '',
                'PASSWORD': u.password or '',
                'HOST': u.hostname or '',
                'PORT': str(u.port or ('3306' if 'mysql' in engine else '5432')),
                'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
            }
        }
        if 'mysql' in engine:
            DATABASES['default']['OPTIONS'] = {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                'charset': 'utf8mb4',
            }
        elif 'postgresql' in engine:
            query_params = parse_qs(u.query)
            sslmode = query_params.get('sslmode', ['require'])[0]
            DATABASES['default']['OPTIONS'] = {'sslmode': sslmode}
    DB_ENGINE = DATABASES['default'].get('ENGINE', 'django.db.backends.postgresql')
else:
    if DB_ENGINE == 'django.db.backends.sqlite3':
        DATABASES = {
            'default': {
                'ENGINE': DB_ENGINE,
                'NAME': os.environ.get('DB_NAME', str(BASE_DIR / 'ci.sqlite3')),
            }
        }
    else:
        DATABASES = {
            'default': {
                'ENGINE': DB_ENGINE,
                'NAME': os.environ.get('DB_NAME', 'ecommerce_inteligente'),
                'USER': os.environ.get('DB_USER', 'root'),
                'PASSWORD': os.environ.get('DB_PASSWORD', ''),
                'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
                'PORT': os.environ.get('DB_PORT', '3306'),
                'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
                'OPTIONS': {
                    'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                    'charset': 'utf8mb4',
                },
            }
        }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-pt'
LANGUAGES = (
    ('pt-pt', 'Português'),
    ('en', 'English'),
)
TIME_ZONE = 'Africa/Luanda'
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
    os.path.join(BASE_DIR, 'img'),
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = os.environ.get('MEDIA_URL', '/media/')
MEDIA_CDN_URL = os.environ.get('MEDIA_CDN_URL', '').strip().rstrip('/')
if MEDIA_CDN_URL:
    MEDIA_URL = f'{MEDIA_CDN_URL}/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get('FILE_UPLOAD_MAX_MEMORY_SIZE', str(5 * 1024 * 1024)))
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.environ.get('DATA_UPLOAD_MAX_MEMORY_SIZE', str(10 * 1024 * 1024)))

MEDIA_STORAGE_BACKEND = os.environ.get(
    'MEDIA_STORAGE_BACKEND',
    'django.core.files.storage.FileSystemStorage',
)
REQUIRE_EXTERNAL_MEDIA_STORAGE = _env_bool(
    'REQUIRE_EXTERNAL_MEDIA_STORAGE',
    False,
)
if REQUIRE_EXTERNAL_MEDIA_STORAGE and MEDIA_STORAGE_BACKEND == 'django.core.files.storage.FileSystemStorage':
    raise ImproperlyConfigured(
        'Configure um storage externo para media em produção (S3/MinIO ou equivalente).'
    )

if MEDIA_STORAGE_BACKEND == 'django.core.files.storage.FileSystemStorage':
    os.makedirs(MEDIA_ROOT, exist_ok=True)
    os.makedirs(os.path.join(MEDIA_ROOT, 'produtos'), exist_ok=True)

AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', '') or None
AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', '') or None
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '') or None
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '') or None
AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN', '') or None
AWS_S3_QUERYSTRING_AUTH = _env_bool('AWS_S3_QUERYSTRING_AUTH', True)
AWS_S3_FILE_OVERWRITE = False
MEDIA_STORAGE_OPTIONS = {
    'bucket_name': AWS_STORAGE_BUCKET_NAME,
    'region_name': AWS_S3_REGION_NAME,
    'endpoint_url': AWS_S3_ENDPOINT_URL,
    'access_key': AWS_ACCESS_KEY_ID,
    'secret_key': AWS_SECRET_ACCESS_KEY,
    'custom_domain': AWS_S3_CUSTOM_DOMAIN,
    'querystring_auth': AWS_S3_QUERYSTRING_AUTH,
    'file_overwrite': AWS_S3_FILE_OVERWRITE,
}
STORAGES = {
    'default': {
        'BACKEND': MEDIA_STORAGE_BACKEND,
        **({'OPTIONS': MEDIA_STORAGE_OPTIONS} if MEDIA_STORAGE_BACKEND != 'django.core.files.storage.FileSystemStorage' else {}),
    },
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if (DEBUG or _env_bool('VERCEL', False))
            else 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
        ),
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
AUTHENTICATION_BACKENDS = ['loja.auth_backends.UsernameOrEmailBackend']

SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_AGE = 1209600
if not USE_REDIS_CACHE:
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'
else:
    SESSION_ENGINE = os.environ.get('SESSION_ENGINE', 'django.contrib.sessions.backends.cached_db')
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'SAMEORIGIN'
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache' if USE_REDIS_CACHE else 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': REDIS_URL if USE_REDIS_CACHE else 'mira-commerce-cache',
        'TIMEOUT': CACHE_TIMEOUT,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        } if USE_REDIS_CACHE else {},
        'KEY_PREFIX': 'miracommerce',
    }
}
if not DEBUG and not TESTING and not IS_COLLECTSTATIC:
    engine = DATABASES['default'].get('ENGINE', '')
    if 'sqlite' not in engine and not DATABASES['default'].get('PASSWORD'):
        raise ImproperlyConfigured('DB_PASSWORD deve ser definida em produção.')

if not DEBUG and MEDIA_STORAGE_BACKEND != 'django.core.files.storage.FileSystemStorage':
    if not AWS_STORAGE_BUCKET_NAME:
        raise ImproperlyConfigured('AWS_STORAGE_BUCKET_NAME deve ser definida para o storage externo.')
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        raise ImproperlyConfigured('Credenciais do storage externo devem ser definidas em produção.')
    if not MEDIA_CDN_URL:
        raise ImproperlyConfigured(
            'MEDIA_CDN_URL deve apontar para a origem HTTPS das imagens externas em produção.'
        )

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = _env_bool('CELERY_TASK_ALWAYS_EAGER', DEBUG or _env_bool('VERCEL', False))
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_TIME_LIMIT = int(os.environ.get('CELERY_TASK_TIME_LIMIT', '900'))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.environ.get('CELERY_TASK_SOFT_TIME_LIMIT', '840'))
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    'atualizar-promocoes-a-cada-15-minutos': {
        'task': 'loja.atualizar_promocoes',
        'schedule': 900,
    },
    'recalcular-recomendacoes-a-cada-hora': {
        'task': 'loja.gerar_regras_associacao',
        'schedule': 3600,
    },
    'anonimizar-usuarios-inativos-diariamente': {
        'task': 'loja.anonimizar_usuarios_inativos',
        'schedule': 86400,
    },
}

SIMPLEUI_HOME_TITLE = 'MiraComerce IA - Gestão de Vendas'
SIMPLEUI_HOME_INFO = False
SIMPLEUI_HOME_QUICK_CREATE = True
SIMPLEUI_DEFAULT_THEME = 'ant.design'

SIMPLEUI_ICON = {
    'Produtos': 'fas fa-shopping-basket',
    'Categorias': 'fas fa-layer-group',
    'Vendas': 'fas fa-money-bill-wave',
    'Clientes': 'fas fa-user-friends',
    'Pedidos': 'fas fa-boxes-packing',
    'Pagamentos': 'fas fa-credit-card',
    'Movimentacao estoques': 'fas fa-warehouse',
    'Historico status pedidos': 'fas fa-timeline',
    'Auditoria administrativas': 'fas fa-shield-halved',
    'Zonas de entrega': 'fas fa-map-location-dot',
}

# Em desenvolvimento ou sem credenciais SMTP, exibe os e-mails no console.
# Em produção com credenciais configuradas, utiliza o envio SMTP real.
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '').strip()
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '').strip()

if not EMAIL_HOST_PASSWORD or EMAIL_HOST_USER in ('seu-email@gmail.com', ''):
    EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
else:
    EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')

EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() in ('1', 'true', 'yes', 'on')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'MiraComerce IA <no-reply@miracommerce.app>')
SERVER_EMAIL = os.environ.get('SERVER_EMAIL', EMAIL_HOST_USER or 'no-reply@miracommerce.app')

if not DEBUG and not TESTING and not IS_COLLECTSTATIC and not _env_bool('VERCEL', False):
    if (
        not EMAIL_HOST_USER
        or not EMAIL_HOST_PASSWORD
        or EMAIL_HOST_USER == 'seu-email@gmail.com'
    ):
        raise ImproperlyConfigured('Configure EMAIL_HOST_USER e EMAIL_HOST_PASSWORD em produção.')

if not DEBUG and not CSRF_TRUSTED_ORIGINS:
    raise ImproperlyConfigured('CSRF_TRUSTED_ORIGINS deve ser definida em produção.')

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = False if _env_bool('VERCEL', False) else ENABLE_SECURE_REDIRECT
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'SAMEORIGIN'
    CSP_ENFORCE = _env_bool('CSP_ENFORCE', True)
    CSP_REPORT_URI = os.environ.get('CSP_REPORT_URI', '').strip()
    CSP_ALLOW_INLINE_STYLE_ATTRIBUTES = _env_bool('CSP_ALLOW_INLINE_STYLE_ATTRIBUTES', True)
else:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    CSP_ENFORCE = _env_bool('CSP_ENFORCE', False)
    CSP_REPORT_URI = os.environ.get('CSP_REPORT_URI', '').strip()
    CSP_ALLOW_INLINE_STYLE_ATTRIBUTES = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'formatters': {
        'json': {
            '()': 'loja.observability.JsonFormatter',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO' if DEBUG else 'WARNING',
    },
}

SENTRY_DSN = os.environ.get('SENTRY_DSN', '').strip()
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
        profiles_sample_rate=float(os.environ.get('SENTRY_PROFILES_SAMPLE_RATE', '0.0')),
        environment=os.environ.get('SENTRY_ENVIRONMENT', 'production' if not DEBUG else 'development'),
        send_default_pii=False,
    )
