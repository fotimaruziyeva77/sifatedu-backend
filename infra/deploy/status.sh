#!/usr/bin/env bash
# Server holati — natijani dasturchiga yuborsa bo'ladi (maxfiy qiymatlar chiqmaydi):
#   bash infra/deploy/status.sh
set -uo pipefail
# shellcheck source=infra/deploy/common.sh
. "$(dirname "$0")/common.sh"

section() { printf '\n== %s\n' "$*"; }

section "Versiya"
git log -1 --format='backend:  %h %cd %s' --date=short
git -C frontend log -1 --format='frontend: %h %cd %s' --date=short

section "Konteynerlar"
"${COMPOSE[@]}" ps --format 'table {{.Service}}\t{{.Status}}'

section "Sayt (HTTPS orqali)"
for path in /healthz /api/v1/health/; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
        --resolve "$HOST:443:127.0.0.1" "$APP_URL$path")
    echo "$APP_URL$path → $code"
done

section "Sertifikat (muddati)"
for name in "$HOST" "media.$HOST"; do
    end=$(echo | openssl s_client -connect 127.0.0.1:443 -servername "$name" 2> /dev/null |
        openssl x509 -noout -enddate 2> /dev/null)
    echo "$name: ${end:-sertifikat topilmadi}"
done

section "Telegram bot webhook"
"${COMPOSE[@]}" exec -T backend python manage.py telegram_webhook info 2>&1 |
    grep -viE "secret|token" | head -n 8

section "Zaxira (oxirgi 3 ta)"
ls -1t backups/ 2> /dev/null | head -n 3 || echo "zaxira yo'q"

section "Disk, xotira, yuklama"
df -h / | tail -n 1
free -h | sed -n '2,3p'
uptime
