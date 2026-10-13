"""O'qituvchi o'z guruhini boshqaradi: o'quvchi qo'shish va chiqarish, haftalik dars jadvali.

O'quvchi telefon raqami bilan qo'shiladi. Raqam tizimda bo'lmasa — parolsiz akkaunt yaratiladi:
o'quvchi botga shu raqam bilan kirganda Telegram'i shu akkauntga ulanadi
(`apps.bot.accounts.register`). Xodim akkauntini o'quvchi qilib bo'lmaydi.

Jadval o'zgarsa, kelgusi darslar 14 kun oldinga qayta moslanadi (`apps.live.services.sync`) —
yo'qlama shu darslarda belgilanadi.
"""

import re
from dataclasses import dataclass
from datetime import time

from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import translation
from django.utils.translation import gettext as _

from apps.live import services as live
from apps.live.models import ScheduleSlot
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.notifications.texts import locale_of, text
from apps.users.models import User
from apps.users.roles import Role

from .models import Enrollment, StudyGroup

PHONE = re.compile(r"^\+998\d{9}$")
SHORT_DAYS = ("Du", "Se", "Chor", "Pay", "Ju", "Sha", "Yak")


class RosterError(ValueError):
    """O'qituvchiga ko'rsatiladigan sabab (API 400)."""


def notify_course_opened(enrollment: Enrollment) -> None:
    """Kurs qo'lda ochildi (admin yoki o'qituvchi): o'quvchiga kabinet va Telegram orqali xabar."""
    user = enrollment.user
    locale = locale_of(user.locale)
    with translation.override(locale):
        course = str(enrollment.course.title)
    notify(
        user,
        Notification.Kind.COURSE_OPENED,
        title=text(locale, "opened_title"),
        body=text(locale, "opened_body", course=course),
        link=f"/dashboard/courses/{enrollment.course.slug}",
        dedupe_key=f"opened:{enrollment.pk}",
    )


def normalize_phone(raw: str) -> str:
    digits = "".join(char for char in raw if char.isdigit())
    if len(digits) == 9:
        digits = "998" + digits
    phone = "+" + digits
    if not PHONE.match(phone):
        raise RosterError(_("Telefon raqami noto'g'ri: +998 XX XXX XX XX ko'rinishida yozing."))
    return phone


@dataclass(frozen=True)
class Added:
    user: User
    created: bool  # yangi akkaunt (botga hali kirmagan)
    moved_from: str  # boshqa guruhdan o'tkazildi — eski guruh nomi


@transaction.atomic
def add_student(group: StudyGroup, *, phone: str, first_name: str, last_name: str = "") -> Added:
    phone = normalize_phone(phone)
    first_name, last_name = first_name.strip()[:150], last_name.strip()[:150]
    user = User.objects.select_for_update().filter(phone=phone).first()
    created = user is None
    if user is None:
        if not first_name:
            raise RosterError(_("O'quvchining ismini yozing."))
        user = User.objects.create_user(phone=phone, first_name=first_name, last_name=last_name)
        user.groups.add(Group.objects.get_or_create(name=Role.STUDENT)[0])
    else:
        if user.is_staff or user.is_superuser:
            raise RosterError(_("Bu raqam xodimga tegishli — o'quvchi qilib qo'shib bo'lmaydi."))
        if not user.is_active:
            raise RosterError(_("Bu akkaunt bloklangan."))
        names = {"first_name": first_name, "last_name": last_name}
        blank = [field for field, value in names.items() if value and not getattr(user, field)]
        for field in blank:
            setattr(user, field, names[field])
        if blank:
            user.save(update_fields=blank)
    # Faqat yozilishni qulflaymiz: guruh bo'sh bo'lishi mumkin (outer join qulflanmaydi).
    enrollment = (
        Enrollment.objects.select_for_update(of=("self",))
        .select_related("group")
        .filter(user=user, course_id=group.course_id)
        .first()
    )
    moved_from, opened = "", False
    if enrollment is None:
        enrollment = Enrollment.objects.create(
            user=user,
            course_id=group.course_id,
            group=group,
            status=Enrollment.Status.ACTIVE,
            source=Enrollment.Source.MANUAL,
            study_format=group.study_format,
        )
        opened = True
    else:
        active = enrollment.status == Enrollment.Status.ACTIVE
        if active and enrollment.group_id == group.pk:
            raise RosterError(_("Bu o'quvchi allaqachon shu guruhda."))
        if active and enrollment.group is not None:
            moved_from = enrollment.group.name
        if not active:
            # Qaytgan o'quvchi: kurs qo'lda, muddatsiz ochiladi (admin panelidagi kabi).
            enrollment.status = Enrollment.Status.ACTIVE
            enrollment.source = Enrollment.Source.MANUAL
            enrollment.expires_at = None
            opened = True
        enrollment.group = group
        enrollment.study_format = group.study_format
        enrollment.save(
            update_fields=["status", "source", "expires_at", "group", "study_format", "updated_at"]
        )
    if opened:
        transaction.on_commit(lambda: notify_course_opened(enrollment))
    return Added(user, created, moved_from)


@transaction.atomic
def remove_student(group: StudyGroup, user_id: int) -> User:
    """Guruhdan chiqarish: yozilish bekor qilinadi (kursga kirish yopiladi), tarix qoladi."""
    enrollment = (
        Enrollment.objects.select_for_update(of=("self",))
        .select_related("user")
        .filter(group=group, user_id=user_id, status=Enrollment.Status.ACTIVE)
        .first()
    )
    if enrollment is None:
        raise RosterError(_("Bu o'quvchi guruhda yo'q."))
    enrollment.status = Enrollment.Status.CANCELLED
    enrollment.save(update_fields=["status", "updated_at"])
    return enrollment.user


# --- Jadval ---


def describe(slots: list[ScheduleSlot]) -> str:
    """Guruh kartasi uchun qisqa jadval: «Du, Chor, Ju — 18:00» yoki «Du 18:00, Pay 19:30»."""
    if not slots:
        return ""
    times = {slot.starts_at for slot in slots}
    if len(times) == 1:
        days = ", ".join(SHORT_DAYS[slot.weekday] for slot in slots)
        return f"{days} — {slots[0].starts_at:%H:%M}"
    return ", ".join(f"{SHORT_DAYS[slot.weekday]} {slot.starts_at:%H:%M}" for slot in slots)


def refresh_schedule(group: StudyGroup) -> None:
    group.schedule = describe(list(group.slots.order_by("weekday", "starts_at")))[:120]
    group.save(update_fields=["schedule"])
    live.sync(group)


@transaction.atomic
def add_slot(
    group: StudyGroup, *, weekday: int, starts_at: time, duration_min: int
) -> ScheduleSlot:
    if group.status == StudyGroup.Status.FINISHED:
        raise RosterError(_("Guruh tugagan — jadval qo'yilmaydi."))
    if group.slots.filter(weekday=weekday, starts_at=starts_at).exists():
        raise RosterError(_("Bu kun va soatda dars bor."))
    slot = ScheduleSlot.objects.create(
        group=group, weekday=weekday, starts_at=starts_at, duration_min=duration_min
    )
    refresh_schedule(group)
    return slot


@transaction.atomic
def remove_slot(group: StudyGroup, slot_id: int) -> None:
    deleted, _rows = group.slots.filter(pk=slot_id).delete()
    if not deleted:
        raise RosterError(_("Bunday dars jadvalda yo'q."))
    refresh_schedule(group)
