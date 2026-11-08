#!/usr/bin/env bash
set -Eeuo pipefail

# Teste isolado do caminho S3: os binários externos são substituídos por mocks
# para garantir que diretórios de media não são passados ao sha256sum.
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT
MOCK_BIN="$TEST_ROOT/bin"
mkdir -p "$MOCK_BIN"

cat > "$MOCK_BIN/mysqldump" <<'EOF'
#!/usr/bin/env bash
printf 'CREATE TABLE backup_test (id int);\n'
EOF

cat > "$MOCK_BIN/aws" <<'EOF'
#!/usr/bin/env bash
set -Eeuo pipefail
destination="$4"
mkdir -p "$destination/produtos"
printf 'imagem de teste\n' > "$destination/produtos/item.txt"
EOF

chmod +x "$MOCK_BIN/mysqldump" "$MOCK_BIN/aws"

PATH="$MOCK_BIN:$PATH" \
BACKUP_ROOT="$TEST_ROOT/backups" \
DB_HOST=database DB_NAME=miracommerce DB_USER=backup DB_PASSWORD=secret \
AWS_STORAGE_BUCKET_NAME=media-bucket MEDIA_BACKUP_MODE=s3 \
bash deploy/backup/backup.sh >/dev/null

TARGET="$(find "$TEST_ROOT/backups" -mindepth 1 -maxdepth 1 -type d -print -quit)"
test -n "$TARGET"
grep -q 'media/produtos/item.txt' "$TARGET/SHA256SUMS"
grep -q 'manifest.txt' "$TARGET/SHA256SUMS"
sha256sum --check "$TARGET/SHA256SUMS" >/dev/null
