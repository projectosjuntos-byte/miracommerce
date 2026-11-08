# Suporte automatico a PyMySQL caso mysqlclient nao esteja compilado no ambiente (Vercel/Serverless)
try:
    import MySQLdb  # noqa: F401
except ImportError:
    try:
        import pymysql
        pymysql.version_info = (2, 2, 8, "final", 0)
        pymysql.install_as_MySQLdb()
    except ImportError:
        pass

from .celery import app as celery_app

__all__ = ('celery_app',)
