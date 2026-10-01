"""Offlayn guruhda dars vazifalari (test, uy vazifasi) qachon ochiladi.

Ustoz "Dars o'tildi" deb belgilagan eng oxirgi dargacha hammasi ochiq: oldingi darslarni bittalab
belgilash shart emas. Onlayn va guruhsiz o'quvchilarga bu cheklov yo'q (ularda — 14-qadamdagi
test qoidasi). Video va materiallar cheklanmaydi.
"""

from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.catalog.models import Course, Lesson
from apps.learning.models import Enrollment, StudyGroup

from .models import GroupLesson


def offline_group(user: Any, course_id: int) -> StudyGroup | None:
    """O'quvchining shu kursdagi offlayn guruhi (to'lov muddati o'tmagan yozilish bo'yicha)."""
    if not getattr(user, "is_authenticated", False):
        return None
    enrollment = (
        Enrollment.objects.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
            user=user,
            course_id=course_id,
            status=Enrollment.Status.ACTIVE,
            group__study_format="OFFLINE",
        )
        .select_related("group")
        .first()
    )
    return enrollment.group if enrollment else None


def lesson_order(course_id: int) -> list[int]:
    return list(
        Lesson.objects.filter(module__course_id=course_id)
        .order_by("module__order", "module__id", "order", "id")
        .values_list("id", flat=True)
    )


def closed_lessons(user: Any, course: Course | int) -> set[int]:
    """Vazifalari hali yopiq darslar (offlayn guruh o'quvchisi uchun); boshqalarga — bo'sh."""
    course_id = course if isinstance(course, int) else course.pk
    group = offline_group(user, course_id)
    if group is None:
        return set()
    order = lesson_order(course_id)
    covered = set(GroupLesson.objects.filter(group=group).values_list("lesson_id", flat=True))
    reached = [index for index, lesson_id in enumerate(order) if lesson_id in covered]
    return set(order[(max(reached) if reached else -1) + 1 :])


def tasks_open(user: Any, lesson: Lesson) -> bool:
    return lesson.pk not in closed_lessons(user, lesson.module.course_id)
