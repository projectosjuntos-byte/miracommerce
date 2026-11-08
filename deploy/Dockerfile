FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --create-home --uid 10001 appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN DEBUG=False \
    SECRET_KEY=build-only-secret-key-not-used-at-runtime-12345678901234567890 \
    ALLOWED_HOSTS=localhost \
    CSRF_TRUSTED_ORIGINS=https://localhost \
    DB_ENGINE=django.db.backends.sqlite3 \
    DB_NAME=/tmp/collectstatic.sqlite3 \
    USE_REDIS_CACHE=False \
    REQUIRE_EXTERNAL_MEDIA_STORAGE=False \
    MEDIA_STORAGE_BACKEND=django.core.files.storage.FileSystemStorage \
    EMAIL_HOST_USER=build@example.invalid \
    EMAIL_HOST_PASSWORD=build-only-password \
    python manage.py collectstatic --noinput

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--workers=3", "--timeout=120", "meu_ecommerce.wsgi:application"]
