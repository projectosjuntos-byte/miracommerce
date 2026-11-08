# Suporte automatico a PyMySQL caso mysqlclient nao esteja compilado no ambiente (Vercel/Linux)
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

from .celery import app as celery_app

__all__ = ('celery_app',)
