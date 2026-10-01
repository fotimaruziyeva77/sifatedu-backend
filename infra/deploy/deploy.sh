#!/usr/bin/env bash
# Yangi versiyani chiqarish (serverda):
#   bash /srv/sifatedu/infra/deploy/deploy.sh
#
# Ikkala repo yangilanadi → image'lar yig'iladi → ishga tushadi → tekshiriladi (konteynerlar va
# https orqali sayt va API). Tekshiruvdan o'tmasa — oldingi image'lar bilan qayta ishga tushadi.
# Migratsiyalar orqaga qaytmaydi, shuning uchun ular faqat qo'shiluvchi qilib yoziladi.
set -Eeuo pipefail
cd "$(dirname "$0")/../.."

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)
IMAGES=(sifatedu-backend sifatedu-backend-video sifatedu-frontend)
APP_URL=$(sed -n "s/^APP_URL=//p" .env | tr -d "\"'")
HOST=${APP_URL#https://}

step() { printf '\n==> %s\n' "$*"; }

containers_healthy() {  # backend va frontend "healthy" bo'lguncha, 5 daqiqagacha
    local service id state ready
    for _ in $(seq 1 60); do
        ready=1
        for service in backend frontend; do
            id=$("${COMPOSE[@]}" ps -q "$service")
            state=$(docker inspect -f '{{.State.Health.Status}}' "$id" 2> /dev/null || echo none)
            [ "$state" = healthy ] || ready=0
        done
        [ "$ready" = 1 ] && return 0
        sleep 5
    done
    return 1
}

site_ok() {  # nginx va TLS orqali, xuddi foydalanuvchi kabi
    local path
    for path in /healthz /api/v1/health/; do
        curl -fsS -o /dev/null --max-time 10 --resolve "$HOST:443:127.0.0.1" "$APP_URL$path" ||
            return 1
    done
}

step "Kod"
git pull --ff-only
git -C frontend pull --ff-only
echo "backend:  $(git log -1 --format='%h %cd %s' --date=short)"
echo "frontend: $(git -C frontend log -1 --format='%h %cd %s' --date=short)"

step "Hozirgi image'lar zaxiraga (:previous)"
for image in "${IMAGES[@]}"; do
    if docker image inspect "$image:latest" > /dev/null 2>&1; then
        docker tag "$image:latest" "$image:previous"
    fi
done

step "Yig'ish"
"${COMPOSE[@]}" build

step "Ishga tushirish"
"${COMPOSE[@]}" up -d --remove-orphans

step "Tekshiruv"
if containers_healthy && site_ok; then
    echo "Tayyor: $APP_URL"
else
    echo "Tekshiruvdan o'tmadi — oldingi versiyaga qaytilmoqda." >&2
    for image in "${IMAGES[@]}"; do
        if docker image inspect "$image:previous" > /dev/null 2>&1; then
            docker tag "$image:previous" "$image:latest"
        fi
    done
    "${COMPOSE[@]}" up -d --no-build
    "${COMPOSE[@]}" ps
    echo "Sababini ko'rish: ${COMPOSE[*]} logs --tail=100 backend frontend" >&2
    exit 1
fi

step "Ishlatilmayotgan eski image'lar tozalanadi (:previous saqlanadi)"
docker image prune -f > /dev/null
docker builder prune -f --filter until=168h > /dev/null
df -h / | tail -n 1
