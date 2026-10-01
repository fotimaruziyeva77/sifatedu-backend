#!/bin/sh
# Faqat local: SeaweedFS (S3-mos storage). Kalitlar root .env'dan olinadi.
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
# ("no free volumes left" xatosi), shuning uchun chegara oshirilgan.
exec weed server \
    -dir=/data \
    -master.volumeSizeLimitMB=1024 \
    -volume.max=40 \
    -s3 \
    -s3.port=8333 \
    -s3.config=/tmp/s3.json
