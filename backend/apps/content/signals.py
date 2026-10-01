"""Landing ma'lumotlari o'zgarganda keshni tozalash."""

from typing import Any

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from apps.catalog.models import Category, Course, Instructor

from .models import (
    Advantage,
    Concern,
    FAQItem,
    HowStep,
    LegalPage,
    SiteSettings,
    Testimonial,
)
from .services import invalidate_site_cache

SITE_MODELS = (
    SiteSettings,
    Advantage,
    Concern,
    HowStep,
    FAQItem,
    Testimonial,
    LegalPage,
    Category,
    Instructor,
    Course,
)


@receiver(post_save)
@receiver(post_delete)
def _invalidate_on_change(sender: type, **kwargs: Any) -> None:
    if sender in SITE_MODELS:
        invalidate_site_cache()


@receiver(m2m_changed, sender=Course.instructors.through)
def _invalidate_on_instructors_change(sender: type, **kwargs: Any) -> None:
    invalidate_site_cache()
