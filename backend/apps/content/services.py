"""Landing uchun ma'lumotlarni yig'ish va keshlash."""

from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Prefetch
from django.utils import translation

from apps.catalog.models import Course, Instructor

from .models import (
    Advantage,
    Concern,
    FAQItem,
    HowStep,
    LegalPage,
    SiteSettings,
    Testimonial,
)
from .serializers import SitePayloadSerializer

SITE_CACHE_TTL = 60 * 10
FEATURED_COURSES_LIMIT = 6


def _cache_key(language: str) -> str:
    return f"site:v2:{language}"


def invalidate_site_cache() -> None:
    cache.delete_many([_cache_key(code) for code, _name in settings.LANGUAGES])


def _collect() -> dict[str, Any]:
    site = SiteSettings.load()
    published_instructors = Instructor.objects.filter(is_published=True)
    published_courses = Course.objects.filter(status=Course.Status.PUBLISHED)

    featured_courses = (
        published_courses.filter(is_featured=True)
        .select_related("category")
        .prefetch_related(Prefetch("instructors", queryset=published_instructors))[
            :FEATURED_COURSES_LIMIT
        ]
    )

    return {
        "settings": site,
        # Faqat haqiqiy raqamlar (TZ 4.1). Darslar va talabalar keyingi qadamlarda qo'shiladi.
        "stats": {
            "courses": published_courses.count(),
            "instructors": published_instructors.count(),
            "lessons": 0,
            "students": 0,
        },
        "advantages": Advantage.objects.filter(is_published=True),
        "concerns": Concern.objects.filter(is_published=True),
        "steps": HowStep.objects.filter(is_published=True),
        "faq": FAQItem.objects.filter(is_published=True),
        "testimonials": (
            Testimonial.objects.filter(is_published=True) if site.show_testimonials else []
        ),
        "featured_courses": featured_courses,
        "instructors": published_instructors if site.show_instructors else [],
        "legal_pages": LegalPage.objects.all(),
    }


def get_site_payload() -> dict[str, Any]:
    """Joriy til uchun landing ma'lumotlari (Redis'da keshlanadi)."""
    language = translation.get_language() or settings.LANGUAGE_CODE
    key = _cache_key(language)
    payload = cache.get(key)
    if payload is None:
        payload = dict(SitePayloadSerializer(_collect()).data)
        cache.set(key, payload, SITE_CACHE_TTL)
    return payload
