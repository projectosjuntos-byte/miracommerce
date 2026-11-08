#!/usr/bin/env bash
set -Eeuo pipefail

# Backup oficial do MiraComerce. O snapshot SQL histórico não é utilizado.
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/miracommerce}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="${BACKUP_ROOT}/${STAMP}"
mkdir -p "$TARGET"

: "${DB_HOST:?DB_HOST é obrigatório}"
: "${DB_PORT:=3306}"
: "${DB_NAME:?DB_NAME é obrigatório}"
: "${DB_USER:?DB_USER é obrigatório}"
: "${DB_PASSWORD:?DB_PASSWORD é obrigatório}"

export MYSQL_PWD="$DB_PASSWORD"
mysqldump \
  --host="$DB_HOST" --port="$DB_PORT" --user="$DB_USER" \
  --single-transaction --routines --triggers --hex-blob \
  --default-character-set=utf8mb4 "$DB_NAME" \
  | gzip -9 > "${TARGET}/database.sql.gz"
unset MYSQL_PWD

if [[ "${MEDIA_BACKUP_MODE:-s3}" == "s3" ]]; then
  : "${AWS_STORAGE_BUCKET_NAME:?AWS_STORAGE_BUCKET_NAME é obrigatório para backup S3}"
  aws_args=()
  [[ -n "${AWS_S3_ENDPOINT_URL:-}" ]] && aws_args+=(--endpoint-url "$AWS_S3_ENDPOINT_URL")
  aws s3 sync "s3://${AWS_STORAGE_BUCKET_NAME}/" "${TARGET}/media/" "${aws_args[@]}"
else
  : "${MEDIA_ROOT:?MEDIA_ROOT é obrigatório para backup local}"
  tar -C "$MEDIA_ROOT" -czf "${TARGET}/media.tar.gz" .
fi

printf 'backup=%s\ncreated_at=%s\ndatabase=%s\nmedia_mode=%s\n' \
  "$TARGET" "$STAMP" "$DB_NAME" "${MEDIA_BACKUP_MODE:-s3}" > "${TARGET}/manifest.txt"
# O backup S3 contém um diretório media/. Gere checksums apenas para ficheiros,
# incluindo os seus conteúdos aninhados, para não passar diretórios ao sha256sum.
find "$TARGET" -type f ! -name 'SHA256SUMS' -print0 \
  | sort -z \
  | xargs -0 -r sha256sum > "${TARGET}/SHA256SUMS"

find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime "+${RETENTION_DAYS}" -exec rm -rf -- {} +
echo "Backup criado em ${TARGET}"
