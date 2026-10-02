# Deploy skriptlari uchun umumiy qism: loyiha papkasi, Docker Compose buyrug'i va sayt manzili.
# Ishlatish (skript boshida): . "$(dirname "$0")/common.sh"
# shellcheck shell=bash

cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1

# Compose fayllari root .env dagi COMPOSE_FILE dan (make-env.sh yozadi: alohida yoki umumiy server).
# Eski .env'da bo'lmasa — alohida server rejimi.
if grep -q '^COMPOSE_FILE=' .env 2> /dev/null; then
    COMPOSE=(docker compose)
else
    COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)
fi

APP_URL=$(sed -n "s/^APP_URL=//p" .env 2> /dev/null | tr -d "\"'")
HOST=${APP_URL#https://}

step() { printf '\n==> %s\n' "$*"; }
