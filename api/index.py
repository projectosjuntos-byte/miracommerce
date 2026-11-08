import os
import sys
from pathlib import Path

# Garante que o diretório raiz do projeto esteja no sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meu_ecommerce.settings')

from django.core.wsgi import get_wsgi_application

# Vercel Serverless Function handler
app = get_wsgi_application()
application = app
handler = app
