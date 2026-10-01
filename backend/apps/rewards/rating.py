"""Reyting: haftalik, oylik va umumiy; kurs yoki guruh bo'yicha (sinfdoshlar orasida).

Ball — shu davrda topilgan XP (shtraflar ayirilgan, bekor qilinganlar hisobga olinmaydi);
umumiy — hamyondagi XP. Ism va familiyaning bosh harfi ko'rsatiladi; "reytingda
ko'rsatilmasin" deganlar ro'yxatda yo'q (o'zi o'z o'rnini baribir ko'radi).
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any

from django.db.models import Q, Sum
from django.utils import timezone

from apps.learning.models import Enrollment, StudyGroup
from apps.users.models import User

from .models import Entry, Wallet

PERIODS = ("week", "month", "all")
SCOPES = ("course", "group")
TOP = 10


@dataclass(frozen=True)
class Scope:
    kind: str
    id: int
    title: str


def period_start(period: str, now: datetime) -> datetime | None:
    local = timezone.localtime(now)
    if period == "week":
        monday = local.date() - timedelta(days=local.weekday())
        return timezone.make_aware(datetime.combine(monday, time.min))
    if period == "month":
        return timezone.make_aware(datetime.combine(local.date().replace(day=1), time.min))
    return None


def short_name(user: User) -> str:
    """ "Aziz V." — ism va familiyaning bosh harfi."""
    first = (user.first_name or "").strip() or "—"
    last = (user.last_name or "").strip()
    return f"{first} {last[0]}." if last else first


def active_enrollments(now: datetime) -> Q:
    return Q(status=Enrollment.Status.ACTIVE) & (Q(expires_at__isnull=True) | Q(expires_at__gt=now))


def scopes(user: Any, *, now: datetime | None = None) -> list[Scope]:
    """O'quvchining kurslari va guruhlari (reyting tanlovi uchun)."""
    now = now or timezone.now()
    rows = (
        Enrollment.objects.filter(active_enrollments(now), user_id=user.pk)
        .select_related("course", "group")
        .order_by("course__order", "course_id")
    )
    found: list[Scope] = []
    for row in rows:
        found.append(Scope("course", row.course_id, str(row.course.title)))
        if row.group_id is not None and row.group is not None:
            found.append(Scope("group", row.group_id, row.group.name))
    return found


def members(kind: str, pk: int, *, now: datetime | None = None) -> set[int]:
    now = now or timezone.now()
    field = "course_id" if kind == "course" else "group_id"
    return set(
        Enrollment.objects.filter(
            active_enrollments(now),
            user__is_active=True,
            user__is_staff=False,
            **{field: pk},
        ).values_list("user_id", flat=True)
    )


def can_view(user: Any, kind: str, pk: int) -> bool:
    if kind not in SCOPES:
        return False
    if any(scope.kind == kind and scope.id == pk for scope in scopes(user)):
        return True
    return kind == "group" and StudyGroup.objects.filter(pk=pk, teacher_id=user.pk).exists()


def scores(ids: set[int], period: str, now: datetime) -> dict[int, int]:
    start = period_start(period, now)
    if start is None:
        return dict(Wallet.objects.filter(user_id__in=ids).values_list("user_id", "xp"))
    rows = (
        Entry.objects.filter(user_id__in=ids, created_at__gte=start, canceled_at__isnull=True)
        .values("user_id")
        .annotate(total=Sum("applied_xp"))
    )
    return {row["user_id"]: max(0, row["total"] or 0) for row in rows}


def board(viewer: Any, kind: str, pk: int, period: str, *, now: datetime | None = None) -> dict:
    """Eng yaxshi 10 ta va ko'ruvchining o'rni (yashirinlar ro'yxatda yo'q)."""
    now = now or timezone.now()
    ids = members(kind, pk, now=now)
    hidden = set(
        Wallet.objects.filter(user_id__in=ids, hidden=True).values_list("user_id", flat=True)
    )
    points = scores(ids, period, now)
    people = {person.pk: person for person in User.objects.filter(pk__in=ids)}
    ranked = sorted(
        (pid for pid in ids if pid not in hidden and points.get(pid, 0) > 0),
        key=lambda pid: (-points.get(pid, 0), short_name(people[pid]), pid),
    )
    top = [
        {
            "place": index,
            "name": short_name(people[pid]),
            "xp": points.get(pid, 0),
            "me": pid == viewer.pk,
        }
        for index, pid in enumerate(ranked[:TOP], 1)
    ]
    mine = None
    if viewer.pk in ids:
        place = ranked.index(viewer.pk) + 1 if viewer.pk in ranked else None
        mine = {"place": place, "xp": points.get(viewer.pk, 0), "hidden": viewer.pk in hidden}
    return {
        "period": period,
        "scope": kind,
        "scope_id": pk,
        "total": len(ranked),
        "top": top,
        "me": mine,
    }


def weekly_winners(*, now: datetime | None = None, limit: int = 3) -> list[tuple[User, int]]:
    """O'tgan haftaning eng yaxshilari (butun markaz bo'yicha, yashirinlarsiz)."""
    now = now or timezone.now()
    local = timezone.localtime(now)
    monday = local.date() - timedelta(days=local.weekday())
    end = timezone.make_aware(datetime.combine(monday, time.min))
    start = end - timedelta(days=7)
    rows = (
        Entry.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            canceled_at__isnull=True,
            user__is_active=True,
            user__is_staff=False,
        )
        .exclude(user__wallet__hidden=True)
        .values("user_id")
        .annotate(total=Sum("applied_xp"))
        .filter(total__gt=0)
        .order_by("-total", "user_id")[:limit]
    )
    people = {
        person.pk: person for person in User.objects.filter(pk__in=[r["user_id"] for r in rows])
    }
    return [(people[row["user_id"]], row["total"]) for row in rows]
