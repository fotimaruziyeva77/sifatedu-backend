"""Kurs sertifikati: shartlar bajarilganda o'zi beriladi; raqam va QR bilan tekshiriladi."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Certificate(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("o'quvchi"),
        on_delete=models.CASCADE,
        related_name="certificates",
    )
    course = models.ForeignKey(
        "catalog.Course",
        verbose_name=_("kurs"),
        on_delete=models.PROTECT,
        related_name="certificates",
    )
    number = models.CharField(_("raqam"), max_length=20, unique=True)
    full_name = models.CharField(
        _("ism-familiya"), max_length=300, help_text=_("Berilgan paytdagi ism (keyin o'zgarmaydi).")
    )
    score = models.PositiveSmallIntegerField(_("ball"), default=0)
    issued_at = models.DateTimeField(_("berilgan"), auto_now_add=True, db_index=True)
    revoked_at = models.DateTimeField(_("bekor qilingan"), null=True, blank=True)
    revoke_reason = models.CharField(_("bekor qilish sababi"), max_length=300, blank=True)

    class Meta:
        verbose_name = _("sertifikat")
        verbose_name_plural = _("sertifikatlar")
        ordering = ("-issued_at",)
        constraints = [
            models.UniqueConstraint(fields=["user", "course"], name="unique_certificate_per_course")
        ]

    def __str__(self) -> str:
        return f"{self.number} · {self.full_name}"

    @property
    def is_valid(self) -> bool:
        return self.revoked_at is None
