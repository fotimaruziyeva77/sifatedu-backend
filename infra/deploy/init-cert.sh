#!/usr/bin/env bash
# Birinchi ishga tushirish va HTTPS sertifikati (Let's Encrypt). DNS yozuvlari serverga
# qaragandan keyin, bir marta:
#   bash infra/deploy/init-cert.sh <e-pochta> [domen]        (standart domen: sifatedu.uz)
#
# Bitta sertifikat uch nom uchun: <domen>, www.<domen>, media.<domen>. Keyin certbot uni o'zi
# yangilaydi (kuniga 2 marta tekshiradi) va nginx'ni qayta yuklaydi (reload-nginx.sh).
set -Eeuo pipefail
cd "$(dirname "$0")/../.."

EMAIL=${1:?"e-pochta kerak: bash infra/deploy/init-cert.sh siz@pochta.uz"}
DOMAIN=${2:-sifatedu.uz}
NAME=sifatedu
LIVE=/etc/letsencrypt/live/$NAME
WEBROOT=$PWD/infra/certbot-www
COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)
HOSTS=("$DOMAIN" "www.$DOMAIN" "media.$DOMAIN")

step() { printf '\n==> %s\n' "$*"; }

step "DNS: uchala nom shu serverga qaraydimi"
ip=$(hostname -I | awk '{print $1}')
for host in "${HOSTS[@]}"; do
    resolved=$(getent ahostsv4 "$host" | awk 'NR == 1 {print $1}')
    if [ "$resolved" != "$ip" ]; then
        echo "$host → ${resolved:-topilmadi}, server IP: $ip." >&2
        echo "DNS'da A yozuvni tekshiring yoki yangilanishini kuting (odatda 5–30 daqiqa)." >&2
        exit 1
    fi
    echo "$host → $ip"
done

step "Ishga tushirish (sertifikat olinguncha vaqtinchalik sertifikat bilan)"
mkdir -p "$WEBROOT/.well-known/acme-challenge"
temporary=0
if [ ! -e "$LIVE/fullchain.pem" ]; then
    mkdir -p "$LIVE"
    openssl req -x509 -nodes -newkey rsa:2048 -days 2 -subj "/CN=$DOMAIN" \
        -keyout "$LIVE/privkey.pem" -out "$LIVE/fullchain.pem" 2> /dev/null
    temporary=1
fi
"${COMPOSE[@]}" up -d
echo "ok" > "$WEBROOT/.well-known/acme-challenge/probe"
for _ in $(seq 1 60); do
    if curl -fsS -o /dev/null --max-time 5 "http://127.0.0.1/.well-known/acme-challenge/probe"; then
        break
    fi
    sleep 5
done
rm -f "$WEBROOT/.well-known/acme-challenge/probe"

step "Let's Encrypt sertifikati"
if [ "$temporary" = 1 ]; then
    # certbot o'zi yaratmagan papkaga yozmaydi; nginx vaqtinchalik sertifikatni xotirada saqlaydi.
    rm -rf "$LIVE"
fi
domains=()
for host in "${HOSTS[@]}"; do domains+=(-d "$host"); done
certbot certonly --webroot -w "$WEBROOT" --cert-name "$NAME" "${domains[@]}" \
    --email "$EMAIL" --agree-tos --no-eff-email --non-interactive \
    --deploy-hook "bash $PWD/infra/deploy/reload-nginx.sh"
bash "$PWD/infra/deploy/reload-nginx.sh"

step "Tekshiruv"
for host in "${HOSTS[@]}"; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "https://$host/" || true)
    echo "https://$host/ → $code"
done
echo "(kutilgani: sayt — 200, www — 301, media — 403: fayllar ro'yxati yopiq)"
echo
echo "Tayyor: https://$DOMAIN — sertifikat avtomatik yangilanadi (systemctl list-timers certbot)."
