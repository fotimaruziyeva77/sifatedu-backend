"""Auth biznes mantig'i: ro'yxatdan o'tish, kirishdagi blok, SMS kod yuborish."""

import logging
import secrets
from dataclasses import asdict
from typing import Any

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone, translation

from apps.content.models import LegalPage
from apps.notifications.tasks import send_sms_task

from .models import SocialAccount, User
from .roles import Role
from .social import SocialProfile
from .tasks import fetch_social_avatar

logger = logging.getLogger(__name__)

LOGIN_FAILURE_LIMIT = 10
LOGIN_LOCK_SECONDS = 15 * 60

# Eskiz'da har bir matn oldindan tasdiqlanadi: shablonni o'zgartirsangiz, qayta tasdiqlating.
SMS_TEMPLATES = {
    "uz": "Sifat Edu: tasdiqlash kodi {code}. Uni hech kimga aytmang.",
    "ru": "Sifat Edu: код подтверждения {code}. Никому его не сообщайте.",
    "en": "Sifat Edu: your code is {code}. Do not share it with anyone.",
}


def send_code_sms(phone: str, code: str) -> None:
    """Kod SMS'i so'rov tilida; tranzaksiya muvaffaqiyatli tugagandan so'ng navbatga qo'yiladi."""
    language = translation.get_language() or "uz"
    template = SMS_TEMPLATES.get(language[:2], SMS_TEMPLATES["uz"])
    text = template.format(code=code)
    transaction.on_commit(lambda: send_sms_task.delay(phone, text))


def _failures_key(phone: str) -> str:
    return f"auth:failures:{phone}"


def is_locked(phone: str) -> bool:
    return int(cache.get(_failures_key(phone), 0)) >= LOGIN_FAILURE_LIMIT


def register_failure(phone: str) -> None:
    """Noto'g'ri parol: hisoblagich birinchi xatodan boshlab 15 daqiqa saqlanadi."""
    key = _failures_key(phone)
    if not cache.add(key, 1, LOGIN_LOCK_SECONDS):
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, LOGIN_LOCK_SECONDS)


def clear_failures(phone: str) -> None:
    cache.delete(_failures_key(phone))


def current_terms_version() -> str:
    """Ro'yxatdan o'tish paytidagi oferta va maxfiylik siyosati versiyalari."""
    pages = LegalPage.objects.filter(
        slug__in=[LegalPage.Slug.OFFER, LegalPage.Slug.PRIVACY]
    ).order_by("slug")
    return ", ".join(f"{page.slug}:{page.version}" for page in pages)


def _student_group() -> Group:
    group, _created = Group.objects.get_or_create(name=Role.STUDENT)
    return group


@transaction.atomic
def create_student(
    *,
    phone: str,
    password: str,
    first_name: str,
    last_name: str,
    locale: str,
    marketing_consent: bool = False,
    referred_by: User | None = None,
) -> User:
    now = timezone.now()
    user = User.objects.create_user(
        phone=phone,
        password=password,
        first_name=first_name,
        last_name=last_name,
        locale=locale,
        terms_accepted_at=now,
        terms_version=current_terms_version(),
        marketing_consent_at=now if marketing_consent else None,
        referred_by=referred_by,
    )
    user.groups.add(_student_group())
    return user


# --- Do'stni taklif qilish ---

# Adashtiradigan belgilar yo'q (0/O, 1/I): kod qo'lda ham yoziladi.
REFERRAL_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
REFERRAL_LENGTH = 8
REFERRAL_COOKIE = "sifat_ref"


def referral_code(user: User) -> str:
    """Shaxsiy taklif kodi: birinchi so'ralganda yaratiladi va o'zgarmaydi."""
    if user.referral_code:
        return user.referral_code
    for _attempt in range(5):
        code = "".join(secrets.choice(REFERRAL_ALPHABET) for _ in range(REFERRAL_LENGTH))
        try:
            with transaction.atomic():
                updated = User.objects.filter(pk=user.pk, referral_code__isnull=True).update(
                    referral_code=code
                )
        except IntegrityError:
            continue  # kod band — boshqasi
        if not updated:  # parallel so'rov allaqachon yaratgan
            user.refresh_from_db(fields=["referral_code"])
            return user.referral_code or ""
        user.referral_code = code
        return code
    raise RuntimeError("Taklif kodini yaratib bo'lmadi")


def referrer(code: str | None) -> User | None:
    """Havoladagi kod egasi (faol akkaunt). Noto'g'ri yoki eski kod — None."""
    code = (code or "").strip().upper()
    if not code or len(code) > REFERRAL_LENGTH * 2:
        return None
    return User.objects.filter(referral_code=code, is_active=True).first()


# --- Google va Telegram ---

PENDING_SOCIAL_KEY = "pending_social"
PENDING_SOCIAL_TTL = 15 * 60


def remember_pending_social(session: Any, profile: SocialProfile) -> None:
    """Telefon so'ralgunga qadar provayder ma'lumoti sessiyada turadi (akkaunt yaratilmaydi)."""
    session[PENDING_SOCIAL_KEY] = {**asdict(profile), "at": timezone.now().timestamp()}


def read_pending_social(session: Any) -> SocialProfile | None:
    data = session.get(PENDING_SOCIAL_KEY)
    if not isinstance(data, dict):
        return None
    if timezone.now().timestamp() - float(data.get("at", 0)) > PENDING_SOCIAL_TTL:
        forget_pending_social(session)
        return None
    fields = {key: value for key, value in data.items() if key != "at"}
    try:
        return SocialProfile(**fields)
    except TypeError:
        forget_pending_social(session)
        return None


def forget_pending_social(session: Any) -> None:
    session.pop(PENDING_SOCIAL_KEY, None)


def find_social_user(profile: SocialProfile) -> User | None:
    account = (
        SocialAccount.objects.filter(provider=profile.provider, uid=profile.uid)
        .select_related("user")
        .first()
    )
    if account is None or not account.user.is_active:
        return None
    changes: dict[str, Any] = {"last_login_at": timezone.now()}
    if account.provider == SocialAccount.Provider.TELEGRAM:
        # Telegram orqali qayta kirdi (xabar yuborishga ruxsat so'raladi): yana yozib ko'ramiz.
        changes["blocked_at"] = None
    SocialAccount.objects.filter(pk=account.pk).update(**changes)
    return account.user


def _fill_missing_profile(user: User, profile: SocialProfile) -> None:
    """Provayder ma'lumoti faqat bo'sh maydonlarga yoziladi: foydalanuvchi kiritgani saqlanadi."""
    updated = []
    if not user.first_name and profile.first_name:
        user.first_name = profile.first_name[:150]
        updated.append("first_name")
    if not user.last_name and profile.last_name:
        user.last_name = profile.last_name[:150]
        updated.append("last_name")
    if updated:
        user.save(update_fields=updated)


@transaction.atomic
def link_social(user: User, profile: SocialProfile) -> SocialAccount:
    """Mavjud akkauntga Google yoki Telegram'ni bog'laydi."""
    account, _created = SocialAccount.objects.update_or_create(
        provider=profile.provider,
        uid=profile.uid,
        defaults={"user": user, "email": profile.email, "last_login_at": timezone.now()},
    )
    _fill_missing_profile(user, profile)
    if profile.avatar_url and not user.avatar:
        transaction.on_commit(lambda: fetch_social_avatar.delay(user.pk, profile.avatar_url))
    return account


@transaction.atomic
def create_social_user(
    profile: SocialProfile,
    phone: str,
    locale: str,
    *,
    marketing_consent: bool = False,
    referred_by: User | None = None,
) -> User:
    """Google yoki Telegram orqali yangi akkaunt. Parol o'rnatilmaydi (kirish provayder orqali)."""
    now = timezone.now()
    user = User.objects.create_user(
        phone=phone,
        password=None,
        first_name=profile.first_name[:150],
        last_name=profile.last_name[:150],
        locale=locale,
        terms_accepted_at=now,
        terms_version=current_terms_version(),
        marketing_consent_at=now if marketing_consent else None,
        referred_by=referred_by,
    )
    user.groups.add(_student_group())
    link_social(user, profile)
    return user
