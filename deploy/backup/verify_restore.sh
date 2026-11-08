#!/usr/bin/env bash
set -Eeuo pipefail

# Teste operacional: restaura em banco temporário, valida migrações e elimina apenas esse banco.
BACKUP_DIR="${1:?Uso: verify_restore.sh /caminho/backup}"
VERIFY_DB="${VERIFY_DB:-miracommerce_restore_$(date -u +%Y%m%d%H%M%S)}"
if [[ ! "$VERIFY_DB" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo 'Nome de banco de verificação inválido.' >&2
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/restore.sh" "$BACKUP_DIR" "$VERIFY_DB"

: "${DB_HOST:?DB_HOST é obrigatório}"
: "${DB_PORT:=3306}"
: "${DB_USER:?DB_USER é obrigatório}"
: "${DB_PASSWORD:?DB_PASSWORD é obrigatório}"
export MYSQL_PWD="$DB_PASSWORD"
TABLES="$(mysql --host="$DB_HOST" --port="$DB_PORT" --user="$DB_USER" "$VERIFY_DB" -Nse "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'django_migrations';")"
test "$TABLES" = "1"
mysql --host="$DB_HOST" --port="$DB_PORT" --user="$DB_USER" -e "DROP DATABASE IF EXISTS $VERIFY_DB;"
unset MYSQL_PWD
echo "Restauração verificada com sucesso"
