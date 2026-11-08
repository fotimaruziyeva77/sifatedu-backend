#!/usr/bin/env bash
# Sifat Edu'ni ko'p markazli tuzilishga o'tkazish (bir marta). Tartib: docs/saas-kochirish.md
#   bash <kod>/infra/deploy/adopt.sh rehearse            — jonli baza nusxasida sinov, saytga tegmaydi
#   bash /srv/sifatedu/infra/deploy/adopt.sh move        — ko'chirish: sayt bir necha daqiqa to'xtaydi
#   bash /srv/sifatedu/infra/deploy/adopt.sh rollback /backups/<fayl>.dump — avvalgi holatga qaytish
set -Eeuo pipefail

ROOT=$(cd "$(dirname "$0")/../.." && pwd)
LIVE=${LIVE:-/srv/sifatedu}
COMPOSE=(docker compose --project-directory "$LIVE")
IMAGES=(sifatedu-backend sifatedu-backend-video sifatedu-frontend)
APPS=(worker worker-ai worker-video)
WEB=(beat frontend backend)

env_value() { sed -n "s/^$1=//p" "$LIVE/.env" | tr -d "\"'"; }
step() { printf '\n==> %s\n' "$*"; }
die() { echo "XATO: $*" >&2; exit 1; }

APP_URL=$(env_value APP_URL)
HOST=${APP_URL#https://}
[ -n "$HOST" ] || die "$LIVE/.env da APP_URL topilmadi"
PG_USER=$(env_value POSTGRES_USER)
PG_USER=${PG_USER:-sifatedu}
PG_DB=$(env_value POSTGRES_DB)
PG_DB=${PG_DB:-sifatedu}

sql() {  # postgres konteynerida; 2-argument — baza nomi
    "${COMPOSE[@]}" exec -T postgres sh -c "psql -v ON_ERROR_STOP=1 -U \"\$POSTGRES_USER\" -d ${2:-postgres} -qc '$1'"
}

site_up() {  # HTTPS orqali, xuddi foydalanuvchi kabi; kurslar ro'yxati — markaz ishlayotgani belgisi
    local path
    for path in /healthz /api/v1/health/ /api/v1/courses/; do
        curl -fsS -o /dev/null --max-time 10 --resolve "$HOST:443:127.0.0.1" "$APP_URL$path" ||
            return 1
    done
}

wait_site() {
    local _
    for _ in $(seq 1 60); do
        site_up && return 0
        sleep 5
    done
    return 1
}

# Navbatdagi va bajarilayotgan vazifalar (broker — Redis 1-baza). Eski kod yuborgan vazifada markaz
# belgisi yo'q: yangi worker uni bajara olmaydi, shuning uchun ko'chirishdan oldin tugashi kerak.
pending_tasks() {
    "${COMPOSE[@]}" exec -T redis sh -c '
        for queue in default bulk ai video; do redis-cli -n 1 llen "$queue"; done
        redis-cli -n 1 hlen unacked' | awk '{ total += $1 } END { print total + 0 }'
}

drain_tasks() {
    local left _
    for _ in $(seq 1 60); do
        left=$(pending_tasks)
        [ "$left" = 0 ] && return 0
        echo "Navbatda: $left"
        sleep 5
    done
    return 1
}

check_data() {  # markaz sxemasida har bir model o'qiladi (jadval yoki ustun yetishmasa — xato)
    "$@" python manage.py tenant_command shell --schema=sifat -c '
from django.apps import apps
from apps.catalog.models import Course
from apps.users.models import User
models = [m for m in apps.get_models() if m._meta.managed and not m._meta.proxy]
for model in models:
    model._default_manager.first()
print("Jadvallar:", len(models), "foydalanuvchi:", User.objects.count(), "kurs:", Course.objects.count())
' | tail -n 1
}

rehearse() {
    local db=sifatedu_sinov image=sifatedu-backend:sinov started
    # Nusxa bilan ishlaydi: Redis'ning alohida bazasi, tashqi xizmatlarga hech narsa ketmaydi.
    DATABASE_URL="postgres://$PG_USER:$(env_value POSTGRES_PASSWORD)@postgres:5432/$db"
    export DATABASE_URL
    trial() {
        docker run --rm --network sifatedu_default --env-file "$LIVE/backend/.env" \
            -e DATABASE_URL -e REDIS_URL=redis://redis:6379/15 \
            -e CELERY_BROKER_URL=redis://redis:6379/15 -e SENTRY_DSN= \
            -e DJANGO_SETTINGS_MODULE=config.settings.prod \
            -e FIRST_CENTER_DOMAINS="$HOST" -e PLATFORM_DOMAIN="platform.$HOST" \
            "$image" "$@"
    }

    step "Yangi kod: backend image"
    docker build --target runtime -t "$image" "$ROOT/backend"

    step "Jonli baza nusxasi: $db"
    sql "DROP DATABASE IF EXISTS $db"
    sql "CREATE DATABASE $db"
    started=$SECONDS
    "${COMPOSE[@]}" exec -T postgres sh -c "pg_dump -U \"\$POSTGRES_USER\" -Fc \"\$POSTGRES_DB\" |
        pg_restore -U \"\$POSTGRES_USER\" --no-owner --no-privileges -d $db"
    echo "Nusxa: $((SECONDS - started)) s (zaxira ham shuncha vaqt oladi)"

    step "Himoya: eski bazada migratsiya to'xtashi kerak (quyidagi xato — kutilgan)"
    if trial python manage.py adopt_center --check; then
        die "tekshiruv eski bazani tanimadi"
    fi

    step "Ko'chirish"
    started=$SECONDS
    trial python manage.py adopt_center
    echo "Ko'chirish: $((SECONDS - started)) s"

    step "Ishga tushishdagi qadamlar"
    trial python manage.py adopt_center --check
    trial python manage.py migrate --noinput --verbosity 0
    trial python manage.py ensure_center

    step "Ma'lumotlar"
    check_data trial

    step "Tozalash"
    sql "DROP DATABASE $db"
    docker image rm "$image" > /dev/null
    echo "Sinov muvaffaqiyatli. Jonli tizimga tegilmadi."
}

move() {
    [ "$ROOT" = "$LIVE" ] || die "bu buyruq $LIVE ichidan ishga tushiriladi"
    [ -d "$LIVE/backend/apps/tenancy" ] || die "kod eski: avval git pull (ikkala repo)"
    local dump
    cd "$LIVE"

    step "Sozlamalar (backend/.env)"
    grep -q '^FIRST_CENTER_DOMAINS=' backend/.env || echo "FIRST_CENTER_DOMAINS=$HOST" >> backend/.env
    grep -q '^PLATFORM_DOMAIN=' backend/.env || echo "PLATFORM_DOMAIN=platform.$HOST" >> backend/.env

    step "Hozirgi image'lar zaxiraga (:previous)"
    for image in "${IMAGES[@]}"; do
        if docker image inspect "$image:latest" > /dev/null 2>&1; then
            docker tag "$image:latest" "$image:previous"
        fi
    done

    step "Yig'ish (sayt hali ishlayapti)"
    "${COMPOSE[@]}" build

    step "Yangi ish kelmasin: sayt va jadval to'xtatiladi"
    "${COMPOSE[@]}" stop "${WEB[@]}"

    step "Bajarilayotgan vazifalar kutiladi (5 daqiqagacha)"
    if ! drain_tasks; then
        "${COMPOSE[@]}" start "${WEB[@]}"
        die "navbat bo'shamadi. Hech narsa o'zgarmadi, sayt qayta ishga tushdi — keyinroq takrorlang"
    fi
    "${COMPOSE[@]}" stop "${APPS[@]}"

    step "To'liq zaxira"
    "${COMPOSE[@]}" run --rm backup backup.sh
    dump=$("${COMPOSE[@]}" run --rm --no-deps -T backup sh -c 'ls -1t /backups/*.dump | head -n 1')
    echo "Zaxira: $dump"

    step "Ko'chirish"
    "${COMPOSE[@]}" run --rm --no-deps -e RUN_MIGRATIONS=0 -e COLLECT_STATIC=0 -e ENSURE_CENTER=0 \
        -e ENSURE_BUCKETS=0 backend python manage.py adopt_center

    step "Ishga tushirish"
    "${COMPOSE[@]}" up -d --no-build --remove-orphans

    step "Tekshiruv"
    if ! wait_site; then
        echo "Sayt javob bermadi. Sababi: dc logs --tail=100 backend frontend" >&2
        echo "Qaytarish: bash $LIVE/infra/deploy/adopt.sh rollback $dump" >&2
        exit 1
    fi
    check_data "${COMPOSE[@]}" exec -T backend
    echo
    echo "Tayyor: $APP_URL"
    echo "Muammo chiqsa: bash $LIVE/infra/deploy/adopt.sh rollback $dump"
}

rollback() {
    local dump=${1:-}
    [ -n "$dump" ] || die "zaxira faylini ko'rsating: rollback /backups/<fayl>.dump"
    cd "$LIVE"

    step "To'xtatish"
    "${COMPOSE[@]}" stop "${WEB[@]}" "${APPS[@]}"

    step "Ko'chirish natijasi o'chiriladi, baza zaxiradan tiklanadi"
    sql 'DROP SCHEMA IF EXISTS sifat CASCADE' "$PG_DB"
    sql 'DROP TABLE IF EXISTS public.tenancy_domain, public.tenancy_center' "$PG_DB"
    "${COMPOSE[@]}" run --rm backup restore.sh "$dump"

    step "Oldingi image'lar"
    for image in "${IMAGES[@]}"; do
        docker tag "$image:previous" "$image:latest"
    done
    # Tiklangan baza eski image bilan ishlaydi; yangi kod yana `move` bilan chiqariladi.
    "${COMPOSE[@]}" up -d --no-build --remove-orphans

    step "Tekshiruv"
    wait_site || die "sayt javob bermadi: dc logs --tail=100 backend frontend"
    echo "Qaytarildi: $APP_URL. Tuzatilguncha deploy.sh ishga tushirilmasin."
}

case "${1:-}" in
    rehearse) rehearse ;;
    move) move ;;
    rollback) rollback "${2:-}" ;;
    *) die "ishlatilishi: adopt.sh rehearse | move | rollback <zaxira>" ;;
esac
