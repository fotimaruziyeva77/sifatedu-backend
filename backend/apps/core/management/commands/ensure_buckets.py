from typing import Any

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "S3 bucket'lari (yopiq va ochiq) mavjudligini tekshiradi va yo'q bo'lsa yaratadi."

    def handle(self, *args: Any, **options: Any) -> None:
        client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            region_name=settings.AWS_S3_REGION_NAME,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        for bucket in (settings.S3_BUCKET_PRIVATE, settings.S3_BUCKET_PUBLIC):
            try:
                client.head_bucket(Bucket=bucket)
                self.stdout.write(f"Bucket bor: {bucket}")
            except ClientError:
                client.create_bucket(Bucket=bucket)
                self.stdout.write(self.style.SUCCESS(f"Bucket yaratildi: {bucket}"))
            self._cors(client, bucket)

    def _cors(self, client: Any, bucket: str) -> None:
        """Brauzer S3'ga o'zi murojaat qiladi (video yuklash va HLS segmentlari)."""
        origins = list(settings.S3_CORS_ORIGINS)
        if not origins:
            return
        try:
            client.put_bucket_cors(
                Bucket=bucket,
                CORSConfiguration={
                    "CORSRules": [
                        {
                            "AllowedHeaders": ["*"],
                            "AllowedMethods": ["GET", "HEAD", "PUT", "POST"],
                            "AllowedOrigins": origins,
                            # Multipart yuklash uchun ETag o'qilishi kerak.
                            "ExposeHeaders": ["ETag"],
                            "MaxAgeSeconds": 3000,
                        }
                    ]
                },
            )
            self.stdout.write(f"CORS o'rnatildi: {bucket} ← {', '.join(origins)}")
        except ClientError as exc:
            self.stderr.write(f"CORS o'rnatilmadi ({bucket}): {exc}")
