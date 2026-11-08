import os
import sys
import traceback
from pathlib import Path

# Garante que a raiz do projeto esteja no sys.path para imports como 'loja'
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meu_ecommerce.settings')

_django_app = None
_init_error = None

try:
    from django.core.wsgi import get_wsgi_application
    _django_app = get_wsgi_application()
except Exception as e:
    _init_error = traceback.format_exc()
    print(f"FATAL: Falha ao inicializar Django WSGI: {_init_error}", file=sys.stderr)

def application(environ, start_response):
    global _django_app, _init_error
    if _django_app is None:
        try:
            from django.core.wsgi import get_wsgi_application
            _django_app = get_wsgi_application()
            _init_error = None
        except Exception:
            _init_error = traceback.format_exc()
            print(f"FATAL: Erro na inicializacao tardia do Django: {_init_error}", file=sys.stderr)
            status = '500 Internal Server Error'
            headers = [('Content-Type', 'text/html; charset=utf-8')]
            start_response(status, headers)
            html = f"<html><body style='font-family:sans-serif;padding:30px;background:#111;color:#eee'><h2>Erro de Inicialização do Django na Vercel</h2><pre style='background:#222;padding:15px;border-radius:6px;color:#ff6b6b;overflow:auto'>{_init_error}</pre></body></html>"
            return [html.encode('utf-8')]

    try:
        return _django_app(environ, start_response)
    except Exception:
        err = traceback.format_exc()
        print(f"FATAL: Erro de requisicao no Django: {err}", file=sys.stderr)
        status = '500 Internal Server Error'
        headers = [('Content-Type', 'text/html; charset=utf-8')]
        start_response(status, headers)
        html = f"<html><body style='font-family:sans-serif;padding:30px;background:#111;color:#eee'><h2>Erro de Execução do Django na Vercel</h2><pre style='background:#222;padding:15px;border-radius:6px;color:#ff6b6b;overflow:auto'>{err}</pre></body></html>"
        return [html.encode('utf-8')]

app = application
handler = application
