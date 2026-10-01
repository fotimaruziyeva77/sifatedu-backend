"""Katalog filtrlari: kategoriya, kimga, shakl, daraja, video tili, narx va qidiruv."""

from django.conf import settings
from django.db.models import Q, QuerySet
from django.utils import translation
from django_filters import rest_framework as filters

from .models import Course

# Saralash: "mashhur" — hozircha bosh sahifadagi tanlanganlar va admin bergan tartib.
# O'quvchilar soni bo'yicha saralash 5-qadamda (sotuvlar paydo bo'lgach) qo'shiladi.
SORT_OPTIONS: dict[str, tuple[str, ...]] = {
    "popular": ("-is_featured", "order", "id"),
    "new": ("-created_at", "id"),
    "price": ("price_online", "id"),
    "-price": ("-price_online", "id"),
}


class CourseFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category__slug")
    level = filters.ChoiceFilter(choices=Course.Level.choices)
    video_language = filters.ChoiceFilter(choices=settings.LANGUAGES)
    audience = filters.ChoiceFilter(choices=Course.Audience.choices)
    study_format = filters.ChoiceFilter(choices=Course.Format.choices)
    is_free = filters.BooleanFilter()
    price_min = filters.NumberFilter(field_name="price_online", lookup_expr="gte")
    price_max = filters.NumberFilter(field_name="price_online", lookup_expr="lte")
    q = filters.CharFilter(method="filter_search", label="Qidiruv")
    sort = filters.ChoiceFilter(
        method="filter_sort",
        choices=[(key, key) for key in SORT_OPTIONS],
        label="Saralash",
    )

    class Meta:
        model = Course
        fields = ("category", "level", "video_language", "audience", "study_format", "is_free")

    def filter_search(self, queryset: QuerySet[Course], name: str, value: str) -> QuerySet[Course]:
        """Joriy tilda va o'zbekchada qidiradi: tarjima bo'lmasa ham kurs topiladi."""
        text = value.strip()
        if not text:
            return queryset
        language = (translation.get_language() or settings.LANGUAGE_CODE)[:2]
        languages = {language, settings.LANGUAGE_CODE}
        condition = Q()
        for code in languages:
            condition |= Q(**{f"title_{code}__icontains": text})
            condition |= Q(**{f"short_description_{code}__icontains": text})
        return queryset.filter(condition)

    def filter_sort(self, queryset: QuerySet[Course], name: str, value: str) -> QuerySet[Course]:
        return queryset.order_by(*SORT_OPTIONS[value])

    @property
    def qs(self) -> QuerySet[Course]:
        queryset: QuerySet[Course] = super().qs
        # Saralash berilmagan bo'lsa ham natija barqaror tartibda bo'ladi (sahifalash uchun).
        if not self.form.cleaned_data.get("sort"):
            return queryset.order_by(*SORT_OPTIONS["popular"])
        return queryset
