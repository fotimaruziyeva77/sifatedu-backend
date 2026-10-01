"""Kurs dasturidagi o'zgarish kurs hajmini (darslar soni, davomiyligi) yangilaydi."""

from typing import Any

from django.db.models import Count, Sum
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Course, Lesson, Module


def refresh_course_totals(course_id: int | None) -> None:
    if course_id is None:
        return
    totals = Lesson.objects.filter(module__course_id=course_id).aggregate(
        lessons=Count("id"), minutes=Sum("duration_min")
    )
    Course.objects.filter(pk=course_id).update(
        lesson_count=totals["lessons"] or 0,
        total_duration_min=totals["minutes"] or 0,
    )


@receiver(post_save, sender=Lesson)
@receiver(post_delete, sender=Lesson)
def _on_lesson_change(instance: Lesson, **kwargs: Any) -> None:
    refresh_course_totals(instance.module.course_id)


@receiver(post_save, sender=Module)
@receiver(post_delete, sender=Module)
def _on_module_change(instance: Module, **kwargs: Any) -> None:
    # Modul o'chirilganda darslari ham ketadi (CASCADE), shuning uchun qayta hisoblanadi.
    refresh_course_totals(instance.course_id)


@receiver(post_save, sender=Lesson)
def _sync_duration_from_video(instance: Lesson, **kwargs: Any) -> None:
    """Tayyor video biriktirilganda dars davomiyligi videodan olinadi.

    Teskari yo'nalish (video keyinroq tayyor bo'lsa) `apps/videos/tasks.py` da.
    """
    video = instance.video
    if video is None or not video.is_ready or not video.duration_sec:
        return
    minutes = max(1, round(video.duration_sec / 60))
    if instance.duration_min == minutes:
        return
    # `update` ishlatiladi: qayta `save` chaqirilsa signal takrorlanadi.
    Lesson.objects.filter(pk=instance.pk).update(duration_min=minutes)
    instance.duration_min = minutes
    refresh_course_totals(instance.module.course_id)
