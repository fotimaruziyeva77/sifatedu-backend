from django.db import models
from django.utils.translation import gettext_lazy as _


class Statistics(models.Model):
    """Jadvalsiz model: faqat "statistikani ko'rish" ruxsati uchun (admin bosh sahifasi)."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = [("view_statistics", _("Statistikani ko'rish"))]
        verbose_name = _("statistika")
        verbose_name_plural = _("statistika")

    def __str__(self) -> str:
        return str(self._meta.verbose_name)
