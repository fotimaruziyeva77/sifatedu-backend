#!/bin/sh
# Backup'dan tiklash. OLDIN ilovani to'xtating (backend, worker'lar), aks holda yozuvlar
# tiklash bilan to'qnashadi.
#
#   docker compose -f docker-compose.yml -f docker-compose.prod.yml stop backend worker worker-video beat
#   docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm backup \
#       restore.sh /backups/sifatedu_2026-09-27_0300.dump
set -eu

FILE="${1:?Ishlatilishi: restore.sh /backups/<fayl>.dump}"
: "${DATABASE_URL:?DATABASE_URL kerak}"

if [ ! -f "${FILE}" ]; then
    echo "Fayl topilmadi: ${FILE}" >&2
    exit 1
fi

echo "[restore] ${FILE} → bazaga. Mavjud jadvallar almashtiriladi."
pg_restore --clean --if-exists --no-owner --no-privileges --single-transaction \
    --dbname="${DATABASE_URL}" "${FILE}"
echo "[restore] tayyor"
