"""Javob yoki vazifa o'chirilsa, uning fayllari storage'dan ham o'chiriladi."""

from typing import Any

from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import SubmissionFile


@receiver(post_delete, sender=SubmissionFile)
def delete_stored_file(sender: type[SubmissionFile], instance: SubmissionFile, **_: Any) -> None:
    name = instance.file.name
    storage = instance.file.storage
    if name:
        # Tranzaksiya bekor bo'lsa, fayl qolishi kerak.
        transaction.on_commit(lambda: storage.delete(name))
