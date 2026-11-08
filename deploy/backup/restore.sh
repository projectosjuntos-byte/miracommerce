#!/usr/bin/env bash
set -Eeuo pipefail

# Restaura em um banco explicitamente informado. Nunca aponta para produção por padrão.
BACKUP_DIR="${1:?Uso: restore.sh /caminho/backup [nome_banco_destino]}"
TARGET_DB="${2:?Informe um banco de destino separado para validar a restauração}"
if [[ ! "$TARGET_DB" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo 'Nome de banco inválido.' >&2
  exit 1
fi

test -f "${BACKUP_DIR}/database.sql.gz"
test -f "${BACKUP_DIR}/SHA256SUMS"
(cd "$BACKUP_DIR" && sha256sum -c SHA256SUMS)

: "${DB_HOST:?DB_HOST é obrigatório}"
: "${DB_PORT:=3306}"
: "${DB_USER:?DB_USER é obrigatório}"
: "${DB_PASSWORD:?DB_PASSWORD é obrigatório}"
export MYSQL_PWD="$DB_PASSWORD"
mysql --host="$DB_HOST" --port="$DB_PORT" --user="$DB_USER" \
  -e "CREATE DATABASE IF NOT EXISTS $TARGET_DB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
gzip -dc "${BACKUP_DIR}/database.sql.gz" | \
  mysql --host="$DB_HOST" --port="$DB_PORT" --user="$DB_USER" "$TARGET_DB"
unset MYSQL_PWD
echo "Restauração concluída no banco ${TARGET_DB}"
