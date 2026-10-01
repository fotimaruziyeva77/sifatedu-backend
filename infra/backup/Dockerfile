# PostgreSQL backup: pg_dump (server bilan bir xil 17-versiya) + ixtiyoriy S3 nusxa.
FROM postgres:17-alpine

RUN apk add --no-cache aws-cli tzdata

COPY backup.sh restore.sh loop.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/backup.sh /usr/local/bin/restore.sh /usr/local/bin/loop.sh \
    && mkdir -p /backups

# Oxirgi nusxa 26 soatdan eski bo'lmasligi kerak (kunlik jadval + zaxira vaqt).
HEALTHCHECK --interval=10m --timeout=30s --start-period=15m --retries=2 \
    CMD test -n "$(find /backups -maxdepth 1 -name 'sifatedu_*.dump' -mmin -1560)"

CMD ["/usr/local/bin/loop.sh"]
