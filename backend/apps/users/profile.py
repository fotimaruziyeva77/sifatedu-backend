"""O'quvchi profili (22d): to'liq ism (familiya, ism, otasining ismi), tug'ilgan sana va rasm.

Pasport ma'lumoti saqlanmaydi. O'quvchi botda to'ldiradi (`apps/bot/profile.py`), o'qituvchi,
admin va menejer kabinetda tuzatadi. Faqat guruhdagi o'quvchidan so'raladi: daraja testiga
kelgan yangi odamning ro'yxatdan o'tishi qisqa qoladi.
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.utils import timezone

from .models import User

NAME = "name"
BIRTH = "birth"
PHOTO = "photo"
MIN_AGE, MAX_AGE = 4, 90
# Har xil tutuq belgisi (o‘, gʻ, ’) bitta ko'rinishga keltiriladi.
APOSTROPHES = str.maketrans(dict.fromkeys("ʻʼ‘’`´", "'"))
WORD = re.compile(r"[^\W\d_]+(?:['-][^\W\d_]+)*'?")
# Otasining ismidagi qo'shimchalar kichik harf bilan qoladi: «Akmal o'g'li».
SUFFIXES = frozenset({"o'g'li", "og'li", "ogli", "qizi", "ўғли", "угли", "қизи", "кизи", "оглы"})
DATE = re.compile(r"(\d{1,2})[./\-\s](\d{1,2})[./\-\s](\d{4})")
ISO_DATE = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")


@dataclass(frozen=True)
class FullName:
    last: str
    first: str
    middle: str = ""


def tidy(word: str) -> str:
    """KATTA yoki kichik yozilgan so'z — bosh harf bilan («VALIYEV» → «Valiyev»)."""
    if word.lower() in SUFFIXES:
        return word.lower()
    if word.isupper() or word.islower():
        return word[:1].upper() + word[1:].lower()
    return word


def parse_name(text: str) -> FullName | None:
    """«Familiya Ism Otasining ismi»: 2–5 so'z, faqat harflar (lotin yoki kirill)."""
    words = text.translate(APOSTROPHES).split()
    if not 2 <= len(words) <= 5:
        return None
    if any(not WORD.fullmatch(word) or not 2 <= len(word) <= 40 for word in words):
        return None
    words = [tidy(word) for word in words]
    return FullName(last=words[0], first=words[1], middle=" ".join(words[2:]))


def age(born: date, today: date) -> int:
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def valid_birth(born: date, today: date | None = None) -> bool:
    return MIN_AGE <= age(born, today or timezone.localdate()) <= MAX_AGE


def parse_birth(text: str, today: date | None = None) -> date | None:
    """«14.03.2008», «14/03/2008», «14-03-2008» yoki «2008-03-14»."""
    value = text.strip()
    if match := DATE.fullmatch(value):
        day, month, year = (int(part) for part in match.groups())
    elif match := ISO_DATE.fullmatch(value):
        year, month, day = (int(part) for part in match.groups())
    else:
        return None
    try:
        born = date(year, month, day)
    except ValueError:
        return None
    return born if valid_birth(born, today) else None


def in_group(user: User) -> bool:
    """Guruhda o'qiyotgan o'quvchi (markazning o'quvchisi)."""
    from apps.learning.models import Enrollment

    return Enrollment.objects.filter(
        user=user, status=Enrollment.Status.ACTIVE, group__isnull=False
    ).exists()


def complete_name(user: User) -> bool:
    return bool(user.first_name.strip() and user.last_name.strip())


def complete(user: User) -> bool:
    """Ism tasdiqlangan va tug'ilgan sana bor (rasm ixtiyoriy)."""
    return user.profile_confirmed_at is not None and user.birth_date is not None


def missing(user: User) -> list[str]:
    """Botda so'raladigan qadamlar (tartib bilan)."""
    steps = []
    if user.profile_confirmed_at is None:
        steps.append(NAME)
    if user.birth_date is None:
        steps.append(BIRTH)
    if not user.avatar:
        steps.append(PHOTO)
    return steps


def needs_profile(user: User) -> bool:
    return not complete(user) and in_group(user)


def save_name(user: User, name: FullName) -> None:
    user.last_name, user.first_name = name.last[:150], name.first[:150]
    user.middle_name = name.middle[:150]
    user.profile_confirmed_at = timezone.now()
    user.save(update_fields=["last_name", "first_name", "middle_name", "profile_confirmed_at"])


def save_birth(user: User, born: date) -> None:
    user.birth_date = born
    user.save(update_fields=["birth_date"])


def update_by_staff(user: User, data: dict[str, Any]) -> None:
    """O'qituvchi, admin yoki menejer tuzatdi: ism tasdiqlangan hisoblanadi (botda qayta
    so'ralmaydi). `photo` — yangi rasm (bayt), `remove_photo` — rasmni olib tashlash."""
    from . import photos

    photo: bytes | None = data.get("photo")
    if photo is not None:
        photos.set_avatar(user, photo)  # PhotoError — boshqa narsa o'zgarmasdan
    elif data.get("remove_photo"):
        photos.remove_avatar(user)
    fields = ["first_name", "last_name", "middle_name", "birth_date"]
    for field in fields:
        if field in data:
            setattr(user, field, data[field])
    if complete_name(user):
        user.profile_confirmed_at = user.profile_confirmed_at or timezone.now()
        fields.append("profile_confirmed_at")
    user.save(update_fields=fields)
