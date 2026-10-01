"""Admin: berilgan sertifikatlar (faqat ko'rish), bekor qilish va qaytarish."""

from typing import Any

from django import forms
from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.forms import BaseDialogForm

from apps.catalog.scope import TeacherScopedAdmin
from apps.core.admin_utils import ActionsOnlyChangeMixin
from apps.notifications.admin import finish

from .models import Certificate


class RevokeForm(BaseDialogForm):
    reason = forms.CharField(
        label=_("Sabab"),
        max_length=300,
        help_text=_("Tekshirish sahifasida «Bekor qilingan» va shu sabab ko'rinadi."),
    )


@admin.register(Certificate)
class CertificateAdmin(ActionsOnlyChangeMixin, TeacherScopedAdmin, ModelAdmin):
    teacher_course_path = "course"
    list_display = ("number", "full_name", "course", "score", "issued_at", "show_valid")
    list_filter = ("course", ("revoked_at", admin.EmptyFieldListFilter))
    search_fields = ("number", "full_name", "user__phone")
    list_select_related = ("course",)
    date_hierarchy = "issued_at"
    fields = (
        "number",
        "user",
        "full_name",
        "course",
        "score",
        "issued_at",
        "revoked_at",
        "revoke_reason",
    )
    readonly_fields = fields
    actions_detail = ("revoke", "restore")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_revoke_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return request.user.has_perm("certificates.change_certificate")

    def has_restore_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return request.user.has_perm("certificates.change_certificate")

    @display(description=_("Holat"), label={True: "success", False: "danger"})
    def show_valid(self, obj: Certificate) -> tuple[bool, str]:
        return obj.is_valid, str(_("Haqiqiy") if obj.is_valid else _("Bekor qilingan"))

    @action(
        description=_("Bekor qilish"),
        url_path="revoke",
        permissions=["revoke"],
        icon="block",
        variant=ActionVariant.DANGER,
        dialog={
            "title": _("Sertifikatni bekor qilish"),
            "description": _("Tekshirish sahifasida «Bekor qilingan» deb chiqadi."),
            "form_class": RevokeForm,
            "form_submit_text": _("Bekor qilish"),
        },
    )
    def revoke(self, request: HttpRequest, form: Any, object_id: int) -> HttpResponse:
        certificate = get_object_or_404(Certificate, pk=object_id)
        reason = str(form.cleaned_data.get("reason") or "") if form is not None else ""
        certificate.revoked_at = timezone.now()
        certificate.revoke_reason = reason.strip()[:300]
        certificate.save(update_fields=["revoked_at", "revoke_reason"])
        messages.success(request, _("Sertifikat bekor qilindi."))
        return finish(request, reverse("admin:certificates_certificate_change", args=[object_id]))

    @action(
        description=_("Qaytarish"),
        url_path="restore",
        permissions=["restore"],
        icon="undo",
    )
    def restore(self, request: HttpRequest, object_id: int) -> HttpResponse:
        Certificate.objects.filter(pk=object_id).update(revoked_at=None, revoke_reason="")
        messages.success(request, _("Sertifikat yana haqiqiy."))
        return finish(request, reverse("admin:certificates_certificate_change", args=[object_id]))
