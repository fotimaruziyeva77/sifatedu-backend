"""Admin uchun umumiy yordamchilar: tarjima qilinadigan maydonlar til tablarida ko'rsatiladi."""

from collections.abc import Sequence
from typing import Any

from django.conf import settings
from django.db import models
from modeltranslation.admin import TranslationAdmin
from unfold.admin import ModelAdmin
from unfold.overrides import FORMFIELD_OVERRIDES as UNFOLD_OVERRIDES

# Django 6.0 sxemasiz manzilga "https://" qo'shadi; hozirdan shu xatti-harakatga o'tiladi.
FORMFIELD_OVERRIDES = {
    **UNFOLD_OVERRIDES,
    models.URLField: {**UNFOLD_OVERRIDES[models.URLField], "assume_scheme": "https"},
}


def language_tabs(fields: Sequence[str]) -> list[Any]:
    """Har bir til uchun alohida tab: `title` → `title_uz`, `title_ru`, `title_en`.

    `list[Any]`: natija admin `fieldsets` ro'yxatiga yoyiladi (django-stubs'ning ichki TypedDict'i
    tashqaridan import qilinmaydi).
    """
    return [
        (
            name,
            {"classes": ["tab"], "fields": [f"{field}_{code}" for field in fields]},
        )
        for code, name in settings.LANGUAGES
    ]


class TranslatedModelAdmin(TranslationAdmin, ModelAdmin):
    """modeltranslation + Unfold. Til maydonlari `language_tabs()` bilan joylashtiriladi."""

    warn_unsaved_form = True
    formfield_overrides = FORMFIELD_OVERRIDES


class ActionsOnlyChangeMixin:
    """Maydonlari faqat o'qish uchun, o'zgarish amallar orqali (masalan, "Bekor qilish") bo'lgan
    sahifa: pastdagi "Saqlash" tugmalari chalg'itmasin."""

    def change_view(
        self, request: Any, object_id: str, form_url: str = "", extra_context: Any = None
    ) -> Any:
        context = {
            **(extra_context or {}),
            "show_save": False,
            "show_save_and_continue": False,
            "show_save_and_add_another": False,
        }
        return super().change_view(request, object_id, form_url, context)  # type: ignore[misc]
