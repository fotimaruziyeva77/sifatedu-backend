#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-0}" = "1" ]; then
    python manage.py collectstatic --noinput --verbosity 0
fi

if [ "${ENSURE_SUPERUSER:-0}" = "1" ]; then
    python manage.py ensure_superuser
fi

if [ "${ENSURE_BUCKETS:-0}" = "1" ]; then
    python manage.py ensure_buckets
fi

exec "$@"
