#!/usr/bin/env bash
# Production sozlamalari: root .env, backend/.env va frontend/.env. Bir marta, serverda:
#   bash infra/deploy/make-env.sh [domen] [alohida|umumiy] [port]
#     alohida (standart) — server faqat Sifat uchun: 80 va 443 Sifat nginx'ida
#     umumiy             — serverda boshqa loyihalar ham bor: 80 va 443 serverdagi nginx'da,
#                          Sifat nginx'i 127.0.0.1:<port> da (standart 8090)
#
# Maxfiy qiymatlar (Django kaliti, baza paroli, S3 va video kalitlari, webhook siri) shu yerda
# tasodifiy yaratiladi. Tashqi kalitlar (bot, Click, Eskiz, AI, Google) so'raladi — ularni faqat
# shu serverda yozing, chatga yubormang. Bo'sh qoldirilganini keyin fayl ichida to'ldirsa bo'ladi
# (so'ng: bash infra/deploy/deploy.sh). Qo'llanma: docs/DEPLOY.md
set -Eeuo pipefail
cd "$(dirname "$0")/../.."

DOMAIN=${1:-sifatedu.uz}
MODE=${2:-alohida}
PROXY_PORT=${3:-8090}
APP_URL="https://$DOMAIN"
MEDIA_URL="https://media.$DOMAIN"

case $MODE in
    alohida)
        files=(docker-compose.yml docker-compose.prod.yml)
        PARALLEL=""
        ;;
    umumiy)
        files=(docker-compose.yml docker-compose.prod.yml docker-compose.proxy.yml)
        # Image'lar birma-bir yig'iladi: boshqa loyihalar uchun xotira birdan kamayib ketmasin.
        PARALLEL="COMPOSE_PARALLEL_LIMIT=1"
        ;;
    *) echo "Rejim: alohida yoki umumiy (berildi: $MODE)" >&2; exit 1 ;;
esac
# To'liq yo'llar: `docker compose --project-directory ...` boshqa papkadan ham to'g'ri ishlasin.
COMPOSE_FILE=""
for file in "${files[@]}"; do COMPOSE_FILE+="${COMPOSE_FILE:+:}$PWD/$file"; done

[ -d frontend ] || { echo "frontend/ papkasi yo'q: avval frontend repozitoriyini klonlang." >&2; exit 1; }
for file in .env backend/.env frontend/.env; do
    if [ -e "$file" ]; then
        echo "$file allaqachon bor — ustidan yozilmaydi. Qaytadan yaratish uchun avval o'chiring." >&2
        exit 1
    fi
done

hex() { openssl rand -hex "$1"; }
token() { openssl rand -base64 64 | tr -d '\n/+=' | cut -c1-"$1"; }

# .env'da qiymat bitta tirnoqda: $ va boshqa belgilar o'zgarmaydi.
quote() { printf "'%s'" "$1"; }

ask() {  # ask VAR "Savol" [standart qiymat]
    local answer
    read -r -p "$2${3:+ [$3]}: " answer
    printf -v "$1" '%s' "${answer:-${3:-}}"
}

secret() {  # secret VAR "Savol" — yozilgani ekranda ko'rinmaydi
    local answer
    while :; do
        read -r -s -p "$2 (ekranda ko'rinmaydi; bo'sh — keyin): " answer
        echo
        case $answer in
            *"'"*) echo "Qiymatda ' belgisi bo'lmasin." ;;
            *) break ;;
        esac
    done
    printf -v "$1" '%s' "$answer"
}

echo "Sifat Edu — production sozlamalari: $APP_URL"
echo "Bo'sh qoldirilgan bo'lim keyin to'ldirilguncha o'chiq turadi."

echo; echo "1/6 Telegram bot"
ask BOT_USERNAME "Bot nomi (@ siz)" "sifat_edubot"
secret BOT_TOKEN "Bot tokeni (@BotFather)"
ask LEADS_CHAT "Arizalar guruhi ID (-100…)"
ask ALERTS_CHAT "Texnik ogohlantirishlar guruhi ID (-100…, ixtiyoriy)"

echo; echo "2/6 Click (to'lov)"
ask CLICK_SERVICE_ID "CLICK_SERVICE_ID"
ask CLICK_MERCHANT_ID "CLICK_MERCHANT_ID"
ask CLICK_MERCHANT_USER_ID "CLICK_MERCHANT_USER_ID"
secret CLICK_SECRET_KEY "CLICK_SECRET_KEY"
ask CLICK_TIN "STIR (fiskal chek uchun; bo'sh — chek yuborilmaydi)"

echo; echo "3/6 Eskiz (SMS)"
ask ESKIZ_EMAIL "Eskiz e-pochtasi"
secret ESKIZ_PASSWORD "Eskiz paroli"

echo; echo "4/6 AI maslahatchi (Google Gemini)"
secret GEMINI_KEY "Gemini API kaliti (aistudio.google.com, billing yoqilgan)"

echo; echo "5/6 Google bilan kirish"
ask GOOGLE_CLIENT_ID "Google OAuth Client ID"

echo; echo "6/6 Sentry — xatolar kuzatuvi (ixtiyoriy)"
ask SENTRY_BACKEND "Sentry DSN (backend)"
ask SENTRY_FRONTEND "Sentry DSN (frontend)"

SMS_DRY_RUN=true
[ -n "$ESKIZ_EMAIL" ] && [ -n "$ESKIZ_PASSWORD" ] && SMS_DRY_RUN=false
FISCAL_DRY_RUN=true
[ -n "$CLICK_TIN" ] && FISCAL_DRY_RUN=false

umask 077

cat > .env <<EOF
# Production — infra/deploy/make-env.sh yaratdi ($(date +%F)). Maxfiy: hech kimga yubormang.
# Docker Compose fayllari ($MODE server); deploy.sh va status.sh ham shundan foydalanadi.
COMPOSE_FILE=$COMPOSE_FILE
# Umumiy serverda Sifat nginx'ining ichki porti (host nginx shu portga uzatadi).
PROXY_PORT=$PROXY_PORT
$PARALLEL

POSTGRES_DB=sifatedu
POSTGRES_USER=sifatedu
POSTGRES_PASSWORD=$(hex 24)

# Fayllar va videolar (SeaweedFS, shu serverda)
S3_ACCESS_KEY=sifatedu-$(hex 4)
S3_SECRET_KEY=$(hex 24)

# Frontend build (brauzerga ketadigan qiymatlar image yig'ilganda yoziladi)
APP_URL=$APP_URL
S3_PUBLIC_URL=$MEDIA_URL/sifat-public
SENTRY_DSN_FRONTEND=$(quote "$SENTRY_FRONTEND")
SENTRY_ENVIRONMENT=production

# Kunlik PostgreSQL zaxirasi (03:00, 30 kun) — backups/ papkasida
BACKUP_HOUR=03
BACKUP_KEEP_DAYS=30
EOF

cat > backend/.env <<EOF
# Production — infra/deploy/make-env.sh yaratdi ($(date +%F)). Maxfiy: hech kimga yubormang.
# Izohlar: backend/.env.example

# --- Django ---
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=$(token 64)
DJANGO_ALLOWED_HOSTS=$DOMAIN,backend,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=$APP_URL
APP_URL=$APP_URL
API_DOCS_ENABLED=false
LOG_FORMAT=json
LOG_LEVEL=INFO

# --- Fayllar va videolar (S3 kalitlari root .env'dan) ---
S3_REGION=us-east-1
S3_PUBLIC_ENDPOINT=$MEDIA_URL
S3_BUCKET_PRIVATE=sifat-private
S3_BUCKET_PUBLIC=sifat-public
S3_CORS_ORIGINS=$APP_URL
MAX_VIDEO_SIZE_MB=2048
VIDEO_PART_SIZE_MB=16
HLS_SIGNED_URL_TTL_SEC=7200
# Video kalitlari shu sir bilan shifrlanadi: o'zgartirilsa, yuklangan videolar ochilmaydi.
VIDEO_KEY_SECRET=$(token 48)

# --- SMS (Eskiz) ---
SMS_DRY_RUN=$SMS_DRY_RUN
ESKIZ_EMAIL=$(quote "$ESKIZ_EMAIL")
ESKIZ_PASSWORD=$(quote "$ESKIZ_PASSWORD")
SMS_PRICE_UZS=100

# --- To'lov (Click) ---
CLICK_SERVICE_ID=$(quote "$CLICK_SERVICE_ID")
CLICK_MERCHANT_ID=$(quote "$CLICK_MERCHANT_ID")
CLICK_MERCHANT_USER_ID=$(quote "$CLICK_MERCHANT_USER_ID")
CLICK_SECRET_KEY=$(quote "$CLICK_SECRET_KEY")
CLICK_MERCHANT_TIN=$(quote "$CLICK_TIN")
FISCAL_DRY_RUN=$FISCAL_DRY_RUN

# --- Kirish ---
GOOGLE_CLIENT_ID=$(quote "$GOOGLE_CLIENT_ID")
TELEGRAM_BOT_USERNAME=$(quote "$BOT_USERNAME")

# --- Telegram ---
TELEGRAM_BOT_TOKEN=$(quote "$BOT_TOKEN")
TELEGRAM_LEADS_CHAT_ID=$(quote "$LEADS_CHAT")
TELEGRAM_ALERTS_CHAT_ID=$(quote "$ALERTS_CHAT")
TELEGRAM_REPORTS_CHAT_ID=
DAILY_REPORT_HOUR=21
TELEGRAM_WEBHOOK_SECRET=$(hex 24)

# --- AI maslahatchi (Google Gemini API) ---
GEMINI_API_KEY=$(quote "$GEMINI_KEY")
GEMINI_MODEL=gemini-3.8-flash
GEMINI_PRICE_INPUT=1.5
GEMINI_PRICE_OUTPUT=7.5
GEMINI_THINKING_LEVEL=low
ASSISTANT_DRY_RUN=false

# --- Monitoring ---
SENTRY_DSN=$(quote "$SENTRY_BACKEND")
SENTRY_ENVIRONMENT=production
RESOURCE_CHECKS=true
EOF

cat > frontend/.env <<EOF
# Production — infra/deploy/make-env.sh yaratdi ($(date +%F)).
NEXT_PUBLIC_APP_URL=$APP_URL
API_INTERNAL_URL=http://backend:8000
NEXT_PUBLIC_S3_PUBLIC_URL=$MEDIA_URL/sifat-public
CSP_EXTRA_ORIGINS=
SENTRY_DSN=$(quote "$SENTRY_FRONTEND")
SENTRY_ENVIRONMENT=production
EOF

chmod 600 .env backend/.env frontend/.env

echo
echo "Yaratildi: .env, backend/.env, frontend/.env (faqat root o'qiy oladi)."
missing=()
[ -n "$BOT_TOKEN" ] || missing+=("Telegram bot tokeni")
[ -n "$CLICK_SECRET_KEY" ] || missing+=("Click (sotib olish tugmasi ko'rinmaydi)")
[ "$SMS_DRY_RUN" = false ] || missing+=("Eskiz (SMS yuborilmaydi)")
[ -n "$GEMINI_KEY" ] || missing+=("Gemini (saytda AI chat ko'rinmaydi)")
[ -n "$GOOGLE_CLIENT_ID" ] || missing+=("Google bilan kirish")
[ "$FISCAL_DRY_RUN" = false ] || missing+=("STIR (fiskal chek yuborilmaydi)")
if [ ${#missing[@]} -gt 0 ]; then
    echo "Keyin to'ldiriladi (backend/.env, so'ng deploy.sh):"
    printf '  - %s\n' "${missing[@]}"
fi

echo
if [ "$MODE" = umumiy ]; then
    echo "Keyingi qadam: docker compose build, so'ng docker compose up -d va serverdagi nginx"
    echo "(infra/deploy/host-nginx.conf, port $PROXY_PORT) — docs/DEPLOY.md, \"Umumiy server\"."
else
    echo "Keyingi qadam: docker compose build, so'ng bash infra/deploy/init-cert.sh <e-pochta>."
fi
