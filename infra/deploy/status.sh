#!/usr/bin/env bash
# Server holati — natijani dasturchiga yuborsa bo'ladi (maxfiy qiymatlar chiqmaydi):
#   bash /srv/sifatedu/infra/deploy/status.sh
set -uo pipefail
cd "$(dirname "$0")/../.."

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)
APP_URL=$(sed -n "s/^APP_URL=//p" .env 2> /dev/null | tr -d "\"'")
HOST=${APP_URL#https://}

section() { printf '\n== %s\n' "$*"; }

section "Versiya"
git log -1 --format='backend:  %h %cd %s' --date=short
git -C frontend log -1 --format='frontend: %h %cd %s' --date=short

section "Konteynerlar"
"${COMPOSE[@]}" ps --format 'table {{.Service}}\t{{.Status}}'

section "Sayt (nginx va TLS orqali)"
for path in /healthz /api/v1/health/; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
        --resolve "$HOST:443:127.0.0.1" "$APP_URL$path")
    echo "$APP_URL$path → $code"
done

section "Sertifikat"
openssl x509 -enddate -noout -in /etc/letsencrypt/live/sifatedu/fullchain.pem 2> /dev/null ||
    echo "sertifikat yo'q (init-cert.sh)"

section "Telegram bot webhook"
"${COMPOSE[@]}" exec -T backend python manage.py telegram_webhook info 2>&1 |
    grep -viE "secret|token" | head -n 8

section "Zaxira (oxirgi 3 ta)"
ls -1t backups/ 2> /dev/null | head -n 3 || echo "zaxira yo'q"

section "Disk, xotira, yuklama"
df -h / | tail -n 1
free -h | sed -n '2,3p'
uptime
