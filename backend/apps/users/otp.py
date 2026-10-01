"""SMS orqali bir martalik kodlar (ro'yxatdan o'tish va parolni tiklash).

- Kod 6 raqam, 5 daqiqa amal qiladi, 5 marta noto'g'ri kiritilsa yopiladi, bir marta ishlatiladi.
- Bazada faqat HMAC xeshi (SECRET_KEY bilan): baza sizib chiqsa ham kodni tiklab bo'lmaydi.
- Bitta raqamga 60 soniyada 1 kod, sutkasiga 5 kod (SMS narxi va suiiste'moldan himoya).
"""

import math
import secrets
from datetime import timedelta

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from .models import OneTimeCode

CODE_LENGTH = 6
CODE_TTL = timedelta(minutes=5)
MAX_ATTEMPTS = 5
RESEND_SECONDS = 60
DAILY_LIMIT = 5


class OtpError(Exception):
    """Kodni yuborish yoki tekshirishdagi xato."""


class OtpCooldownError(OtpError):
    def __init__(self, seconds: int) -> None:
        super().__init__(seconds)
        self.seconds = seconds


class OtpDailyLimitError(OtpError):
    pass


class InvalidCodeError(OtpError):
    """Kod noto'g'ri, muddati o'tgan yoki ishlatilgan (sababi oshkor qilinmaydi)."""


def generate_code() -> str:
    return f"{secrets.randbelow(10**CODE_LENGTH):0{CODE_LENGTH}d}"


def _hash(phone: str, purpose: str, code: str) -> str:
    return salted_hmac(
        "apps.users.otp", f"{phone}:{purpose}:{code}", algorithm="sha256"
    ).hexdigest()


def _cooldown_key(phone: str) -> str:
    return f"otp:cooldown:{phone}"


def issue_code(phone: str, purpose: str, ip: str | None = None) -> str:
    """Yangi kod yaratadi va qaytaradi (yuborish chaqiruvchining vazifasi)."""
    # cache.add atomik: bir vaqtdagi ikki so'rovdan faqat bittasi o'tadi.
    if not cache.add(_cooldown_key(phone), 1, RESEND_SECONDS):
        ttl = getattr(cache, "ttl", None)
        left = ttl(_cooldown_key(phone)) if callable(ttl) else None
        raise OtpCooldownError(int(left) if left and left > 0 else RESEND_SECONDS)

    now = timezone.now()
    sent_today = OneTimeCode.objects.filter(
        phone=phone, created_at__gte=now - timedelta(days=1)
    ).count()
    if sent_today >= DAILY_LIMIT:
        raise OtpDailyLimitError

    code = generate_code()
    with transaction.atomic():
        # Faqat oxirgi kod ishlaydi: oldingilari yopiladi.
        OneTimeCode.objects.filter(phone=phone, purpose=purpose, used_at__isnull=True).update(
            used_at=now
        )
        OneTimeCode.objects.create(
            phone=phone,
            purpose=purpose,
            code_hash=_hash(phone, purpose, code),
            expires_at=now + CODE_TTL,
            ip=ip,
        )
    return code


def consume_code(phone: str, purpose: str, code: str) -> None:
    """Kodni tekshiradi va yopadi. Noto'g'ri bo'lsa `InvalidCodeError`.

    Urinishlar soni tranzaksiya ichida saqlanadi, istisno esa undan keyin ko'tariladi —
    aks holda rollback urinishni "o'chirib" yuborardi.
    """
    now = timezone.now()
    with transaction.atomic():
        otp = (
            OneTimeCode.objects.select_for_update()
            .filter(phone=phone, purpose=purpose, used_at__isnull=True, expires_at__gt=now)
            .order_by("-created_at")
            .first()
        )
        valid = False
        if otp is not None:
            otp.attempts += 1
            valid = constant_time_compare(otp.code_hash, _hash(phone, purpose, code))
            if valid or otp.attempts >= MAX_ATTEMPTS:
                otp.used_at = now
            otp.save(update_fields=["attempts", "used_at"])
    if not valid:
        raise InvalidCodeError


def resend_wait(phone: str) -> int:
    """Keyingi kodgacha qolgan soniyalar (interfeysdagi taymer uchun)."""
    latest = OneTimeCode.objects.filter(phone=phone).order_by("-created_at").first()
    if latest is None:
        return 0
    passed = (timezone.now() - latest.created_at).total_seconds()
    return max(0, math.ceil(RESEND_SECONDS - passed))
