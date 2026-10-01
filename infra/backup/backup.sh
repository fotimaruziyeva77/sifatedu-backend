#!/bin/sh
# Bitta backup: pg_dump (custom format, siqilgan) → /backups, eski nusxalar o'chiriladi,
# BACKUP_S3_BUCKET berilgan bo'lsa nusxa S3'ga ham yuklanadi.
set -eu

: "${DATABASE_URL:?DATABASE_URL kerak}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"
STAMP="$(date +%Y-%m-%d_%H%M)"
FILE="/backups/sifatedu_${STAMP}.dump"

echo "[backup] boshlandi: ${FILE}"
# Avval vaqtinchalik nomga yoziladi: yarim yozilgan fayl "tayyor nusxa" bo'lib qolmasin.
pg_dump --format=custom --no-owner --no-privileges --dbname="${DATABASE_URL}" --file="${FILE}.part"
mv "${FILE}.part" "${FILE}"
echo "[backup] tayyor: $(du -h "${FILE}" | cut -f1)"

# Nusxani tekshirish: arxiv o'qiladimi.
pg_restore --list "${FILE}" > /dev/null
echo "[backup] arxiv tekshirildi"

if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    if [ -n "${BACKUP_S3_ENDPOINT:-}" ]; then
        aws s3 cp "${FILE}" "s3://${BACKUP_S3_BUCKET}/postgres/" --endpoint-url "${BACKUP_S3_ENDPOINT}" --only-show-errors
    else
        aws s3 cp "${FILE}" "s3://${BACKUP_S3_BUCKET}/postgres/" --only-show-errors
    fi
    echo "[backup] S3'ga yuklandi: s3://${BACKUP_S3_BUCKET}/postgres/"
fi

find /backups -maxdepth 1 -name 'sifatedu_*.dump' -mtime "+${KEEP_DAYS}" -print -delete \
    | sed 's/^/[backup] o'"'"'chirildi: /'
