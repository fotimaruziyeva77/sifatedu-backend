#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    # Bitta markazli eski baza `adopt_center`siz migratsiya qilinmaydi.
    python manage.py adopt_center --check
    python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-0}" = "1" ]; then
    python manage.py collectstatic --noinput --verbosity 0
fi

if [ "${ENSURE_CENTER:-0}" = "1" ]; then
    python manage.py ensure_center
fi

if [ "${ENSURE_SUPERUSER:-0}" = "1" ]; then
    # `public`dagisi — platforma paneli uchun, markazdagisi — markaz admin paneli uchun.
    python manage.py ensure_superuser
    python manage.py tenant_command ensure_superuser --schema="${FIRST_CENTER_SCHEMA:-sifat}"
fi

if [ "${ENSURE_BUCKETS:-0}" = "1" ]; then
    python manage.py ensure_buckets
fi

exec "$@"
