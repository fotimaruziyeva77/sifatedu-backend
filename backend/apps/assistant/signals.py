"""AI sozlamalari o'zgarsa, sayt ma'lumotlari keshi tozalanadi (chat ko'rinadimi — shu yerda)."""

from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.content.services import invalidate_site_cache

from .models import AssistantSettings


@receiver(post_save, sender=AssistantSettings)
def _invalidate_site(sender: type, **kwargs: Any) -> None:
    invalidate_site_cache()
