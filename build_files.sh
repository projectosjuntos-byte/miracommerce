#!/bin/bash
# ==============================================================================
# SCRIPT DE BUILD AUTOMÁTICO PARA VERCEL (MIRACOMERCE IA)
# ==============================================================================
set -e

# PEP 668 bypass para ambientes gerenciados da Vercel / uv
export PIP_BREAK_SYSTEM_PACKAGES=1

echo "==> [Vercel Build] 1/3 - Instalando dependencias..."
if command -v uv &> /dev/null; then
    echo "==> Usando uv para instalacao rapida no sistema..."
    uv pip install --system -r requirements.txt
else
    echo "==> Usando pip com --break-system-packages..."
    python3 -m pip install --break-system-packages -r requirements.txt || python3 -m pip install -r requirements.txt
fi

echo "==> [Vercel Build] 2/3 - Coletando arquivos estaticos para Edge CDN..."
python3 manage.py collectstatic --noinput --clear

echo "==> [Vercel Build] 3/3 - Verificando migracoes do banco de dados..."
if [ -n "$DATABASE_URL" ] || [ -n "$DB_HOST" ]; then
    echo "==> Aplicando migracoes no banco remoto..."
    python3 manage.py migrate --noinput || echo "Aviso: Migracoes nao puderam ser aplicadas durante o build estatico."
else
    echo "==> DATABASE_URL/DB_HOST nao definido no build. As migracoes podem ser aplicadas pos-deploy."
fi

echo "==> [Vercel Build] Concluido com sucesso!"
