"""O'qish hodisalaridan keyin sertifikat shartlari qayta tekshiriladi."""

from typing import Any

from django.dispatch import receiver

from apps.core import events

from . import services


@receiver(events.lesson_completed)
@receiver(events.quiz_passed)
@receiver(events.homework_accepted)
@receiver(events.exam_finalized)
def progress_changed(sender: Any, *, user_id: int, course_id: int, **kwargs: Any) -> None:
    services.schedule(user_id, course_id)
