#!/usr/bin/env bash
set -Eeuo pipefail

BACKUP_DIR="${1:?Uso: restore_media.sh /caminho/backup}"
DESTINATION="${2:?Informe um destino separado para a restauração das imagens}"

if [[ -d "${BACKUP_DIR}/media" ]]; then
  : "${AWS_STORAGE_BUCKET_NAME:?AWS_STORAGE_BUCKET_NAME é obrigatório}"
  aws_args=()
  [[ -n "${AWS_S3_ENDPOINT_URL:-}" ]] && aws_args+=(--endpoint-url "$AWS_S3_ENDPOINT_URL")
  aws s3 sync "${BACKUP_DIR}/media/" "s3://${AWS_STORAGE_BUCKET_NAME}/${DESTINATION#/}/" "${aws_args[@]}"
elif [[ -f "${BACKUP_DIR}/media.tar.gz" ]]; then
  mkdir -p "$DESTINATION"
  tar -xzf "${BACKUP_DIR}/media.tar.gz" -C "$DESTINATION"
else
  echo 'Backup não contém uma cópia de media reconhecida.' >&2
  exit 1
fi
echo "Media restaurada em ${DESTINATION}"
