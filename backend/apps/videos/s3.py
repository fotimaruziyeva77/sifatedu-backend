"""S3 bilan ishlash: multipart yuklash va imzolangan havolalar.

Ikki mijoz kerak:
  * `internal` — backend va worker ichki tarmoq orqali ishlaydi (`S3_ENDPOINT`);
  * `browser` — imzolangan havolalar brauzer ko'radigan manzil uchun (`S3_PUBLIC_ENDPOINT`).
Imzo Host sarlavhasini ham qamraydi, shuning uchun havolani brauzer ishlatadigan manzil
bilan imzolash shart.
"""

from functools import lru_cache
from typing import Any
from urllib.parse import quote

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from django.conf import settings

# Yuklash va o'chirish ko'p bo'lmaydi; qisqa timeout bilan osilib qolmaydi.
_CONFIG = Config(
    signature_version="s3v4",
    s3={"addressing_style": "path"},
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=5,
    read_timeout=60,
)


def _client(endpoint: str) -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=endpoint or None,
        region_name=settings.AWS_S3_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        config=_CONFIG,
    )


@lru_cache(maxsize=1)
def internal() -> BaseClient:
    """Konteynerlar ichidan: yuklash, o'chirish, multipart boshqarish."""
    return _client(settings.AWS_S3_ENDPOINT_URL or "")


@lru_cache(maxsize=1)
def browser() -> BaseClient:
    """Faqat imzolash uchun: URL brauzer ko'radigan manzil bilan imzolanadi."""
    return _client(settings.S3_PUBLIC_ENDPOINT or settings.AWS_S3_ENDPOINT_URL or "")


def bucket() -> str:
    return settings.S3_BUCKET_PRIVATE


def start_multipart(key: str, content_type: str) -> str:
    response = internal().create_multipart_upload(
        Bucket=bucket(), Key=key, ContentType=content_type or "application/octet-stream"
    )
    return str(response["UploadId"])


def sign_part(key: str, upload_id: str, part_number: int, ttl: int) -> str:
    return str(
        browser().generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": bucket(),
                "Key": key,
                "UploadId": upload_id,
                "PartNumber": part_number,
            },
            ExpiresIn=ttl,
        )
    )


def finish_multipart(key: str, upload_id: str, parts: list[dict[str, Any]]) -> int:
    """Qismlarni birlashtiradi va yakuniy fayl hajmini qaytaradi."""
    internal().complete_multipart_upload(
        Bucket=bucket(),
        Key=key,
        UploadId=upload_id,
        MultipartUpload={
            "Parts": [
                {"PartNumber": part["part_number"], "ETag": part["etag"]}
                for part in sorted(parts, key=lambda item: int(item["part_number"]))
            ]
        },
    )
    head = internal().head_object(Bucket=bucket(), Key=key)
    return int(head["ContentLength"])


def cancel_multipart(key: str, upload_id: str) -> None:
    internal().abort_multipart_upload(Bucket=bucket(), Key=key, UploadId=upload_id)


def put_file(key: str, path: str, content_type: str) -> None:
    with open(path, "rb") as handle:
        internal().put_object(Bucket=bucket(), Key=key, Body=handle, ContentType=content_type)


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    internal().put_object(Bucket=bucket(), Key=key, Body=data, ContentType=content_type)


def download(key: str, path: str) -> None:
    internal().download_file(Bucket=bucket(), Key=key, Filename=path)


def sign_get(key: str, ttl: int, download_name: str | None = None) -> str:
    """Qisqa muddatli havola. `download_name` berilsa, brauzer faylni shu nom bilan saqlaydi."""
    params: dict[str, Any] = {"Bucket": bucket(), "Key": key}
    if download_name:
        params["ResponseContentDisposition"] = content_disposition(download_name)
    return str(browser().generate_presigned_url("get_object", Params=params, ExpiresIn=ttl))


def content_disposition(name: str) -> str:
    """`attachment` sarlavhasi: lotincha zaxira nom va asl (kirill) nom RFC 5987 bo'yicha."""
    clean = name.replace('"', "").replace("\\", "")
    ascii_name = clean.encode("ascii", "ignore").decode() or "fayl"
    header = f'attachment; filename="{ascii_name}"'
    if ascii_name != clean:
        header += f"; filename*=UTF-8''{quote(clean)}"
    return header


def delete_prefix(prefix: str) -> None:
    """Video o'chirilganda uning barcha fayllarini tozalaydi."""
    client = internal()
    pages = client.get_paginator("list_objects_v2").paginate(Bucket=bucket(), Prefix=prefix)
    for page in pages:
        keys = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        if keys:
            client.delete_objects(Bucket=bucket(), Delete={"Objects": keys})
