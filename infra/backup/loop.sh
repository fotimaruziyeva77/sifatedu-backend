#!/bin/sh
# Har kuni BACKUP_HOUR da bitta backup. Konteyner birinchi marta ishga tushganda, nusxa
# umuman bo'lmasa, darhol bittasi olinadi (yangi server ham himoyasiz qolmasin).
set -u

HOUR="${BACKUP_HOUR:-03}"

if [ -z "$(find /backups -maxdepth 1 -name 'sifatedu_*.dump')" ]; then
    backup.sh || echo "[backup] XATO: birinchi backup olinmadi"
fi

while true; do
    TODAY="$(date +%F)"
    if [ "$(date +%H)" = "${HOUR}" ] && [ ! -f "/backups/.done-${TODAY}" ]; then
        if backup.sh; then
            touch "/backups/.done-${TODAY}"
            find /backups -maxdepth 1 -name '.done-*' -mtime +3 -delete
        else
            echo "[backup] XATO: backup olinmadi, 10 daqiqadan so'ng qayta urinadi"
        fi
    fi
    sleep 600
done
