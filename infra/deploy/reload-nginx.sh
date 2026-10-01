#!/usr/bin/env bash
# Sertifikat yangilangach nginx yangisini o'qiydi (to'xtamasdan). certbot o'zi chaqiradi
# (init-cert.sh dagi --deploy-hook); qo'lda ham ishga tushirsa bo'ladi.
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T nginx nginx -s reload
