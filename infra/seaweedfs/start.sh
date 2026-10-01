#!/bin/sh
# SeaweedFS (S3-mos storage): local'da va production serverda. Kalitlar root .env'dan olinadi.
# Ochiq bucket anonim o'qish uchun ochiq, yopiq bucket faqat kalit bilan.
set -e

cat > /tmp/s3.json <<EOF
{
  "identities": [
    {
      "name": "app",
      "credentials": [{ "accessKey": "${S3_ACCESS_KEY}", "secretKey": "${S3_SECRET_KEY}" }],
      "actions": ["Admin", "Read", "List", "Tagging", "Write"]
    },
    {
      "name": "anonymous",
      "actions": ["Read:${S3_BUCKET_PUBLIC}"]
    }
  ]
}
EOF

# Har bucket alohida "collection" oladi va standart 8 volume video uchun yetmaydi
# ("no free volumes left" xatosi). Local'da 40 ta (40 GB); production'da S3_MAX_VOLUMES=0 —
# diskdagi bo'sh joyga qarab avtomatik.
exec weed server \
    -dir=/data \
    -master.volumeSizeLimitMB=1024 \
    -volume.max="${S3_MAX_VOLUMES:-40}" \
    -s3 \
    -s3.port=8333 \
    -s3.config=/tmp/s3.json
