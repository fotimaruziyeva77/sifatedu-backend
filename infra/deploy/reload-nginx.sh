#!/usr/bin/env bash
# Sertifikat yangilangach nginx yangisini o'qiydi (to'xtamasdan). Alohida serverda certbot o'zi
# chaqiradi (init-cert.sh dagi --deploy-hook); qo'lda ham ishga tushirsa bo'ladi.
set -Eeuo pipefail
# shellcheck source=infra/deploy/common.sh
. "$(dirname "$0")/common.sh"
"${COMPOSE[@]}" exec -T nginx nginx -s reload
