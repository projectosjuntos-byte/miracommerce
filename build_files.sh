#!/bin/bash
# ==============================================================================
# SCRIPT DE BUILD AUTOMÁTICO PARA VERCEL (MIRACOMERCE IA)
# ==============================================================================
set -e

echo "==> [Vercel Build] 1/3 - Configurando ambiente Python..."
if command -v uv &> /dev/null; then
    echo "==> Usando uv para garantir Python 3.11 e ambiente virtual isolado..."
    uv venv --python 3.11 .build_env 2>/dev/null || uv venv .build_env
    source .build_env/bin/activate
    uv pip install -r requirements.txt
    PYTHON_CMD="python"
else
    echo "==> Usando pip..."
    export PIP_BREAK_SYSTEM_PACKAGES=1
    python3 -m pip install -r requirements.txt || pip install -r requirements.txt
    PYTHON_CMD="python3"
fi

echo "==> [Vercel Build] 2/3 - Coletando arquivos estaticos para Edge CDN..."
$PYTHON_CMD manage.py collectstatic --noinput --clear

echo "==> [Vercel Build] 3/3 - Verificando migracoes do banco de dados..."
if [ -n "$DATABASE_URL" ] || [ -n "$DB_HOST" ]; then
    echo "==> Aplicando migracoes no banco remoto..."
    $PYTHON_CMD manage.py migrate --noinput || echo "Aviso: Migracoes nao puderam ser aplicadas durante o build estatico."
else
    echo "==> DATABASE_URL/DB_HOST nao definido no build. As migracoes podem ser aplicadas pos-deploy."
fi

# Remove ambiente temporario para manter o pacote leve
rm -rf .build_env 2>/dev/null || true

echo "==> [Vercel Build] Concluido com sucesso!"
