from typing import Any

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import QuerySet
from django.forms import Field
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm
from unfold.forms import UserChangeForm as UnfoldUserChangeForm
from unfold.forms import UserCreationForm as UnfoldUserCreationForm
from unfold.widgets import UnfoldAdminCheckboxSelectMultipleWidget

from .models import OneTimeCode, SocialAccount, User
from .roles import Role, has_role, role_names, set_roles


def can_manage_roles(user: Any) -> bool:
    """Rol berish va xodimlar akkauntini o'zgartirish — faqat Admin."""
    return bool(user.is_superuser) or has_role(user, Role.ADMIN)


class UserCreationForm(UnfoldUserCreationForm):
    class Meta(UnfoldUserCreationForm.Meta):
        model = User
        fields = ("phone",)
        # Bazaviy formadagi `username` maydoni bizning modelda yo'q.
        field_classes: dict[str, type[Field]] = {}


class UserChangeForm(UnfoldUserChangeForm):
    roles = forms.MultipleChoiceField(
        label=_("Rollar"),
        choices=Role.choices,
        required=False,
        widget=UnfoldAdminCheckboxSelectMultipleWidget,
        help_text=_(
            "O'qituvchi, Menejer, Direktor va Admin rollari admin panelga kirishni o'zi beradi. "
            "Ruxsatlar har bir rol uchun oldindan belgilangan."
        ),
    )

    class Meta(UnfoldUserChangeForm.Meta):
        model = User
        fields = "__all__"
        field_classes: dict[str, type[Field]] = {}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk and "roles" in self.fields:
            self.fields["roles"].initial = list(
                self.instance.groups.filter(name__in=Role.values).values_list("name", flat=True)
            )


class RoleFilter(admin.SimpleListFilter):
    title = _("rol")
    parameter_name = "role"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, str]]:
        return [(role.value, str(role.label)) for role in Role]

    def queryset(self, request: HttpRequest, queryset: QuerySet[User]) -> QuerySet[User]:
        value = self.value()
        return queryset.filter(groups__name=value) if value else queryset


class CourseFilter(admin.SimpleListFilter):
    """Menejer uchun: ro'yxatdan o'tib, kurs tanlamaganlarga qo'ng'iroq qilish."""

    title = _("kurs")
    parameter_name = "course"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, str]]:
        return [("none", str(_("Kurs tanlamagan"))), ("active", str(_("O'qiyapti")))]

    def queryset(self, request: HttpRequest, queryset: QuerySet[User]) -> QuerySet[User]:
        from apps.learning.models import Enrollment
        from apps.payments.models import Order

        if self.value() == "none":
            return queryset.exclude(pk__in=Enrollment.objects.values("user_id")).exclude(
                pk__in=Order.objects.values("user_id")
            )
        if self.value() == "active":
            return queryset.filter(
                pk__in=Enrollment.objects.filter(status=Enrollment.Status.ACTIVE).values("user_id")
            )
        return queryset


class TelegramFilter(admin.SimpleListFilter):
    """Kimga Telegram orqali xabar yetadi."""

    title = _("Telegram")
    parameter_name = "telegram"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, str]]:
        return [
            ("yes", str(_("Ulangan"))),
            ("no", str(_("Ulanmagan"))),
            ("blocked", str(_("Botni bloklagan"))),
        ]

    def queryset(self, request: HttpRequest, queryset: QuerySet[User]) -> QuerySet[User]:
        telegram = SocialAccount.objects.filter(provider=SocialAccount.Provider.TELEGRAM)
        if self.value() == "yes":
            return queryset.filter(pk__in=telegram.values("user_id"))
        if self.value() == "no":
            return queryset.exclude(pk__in=telegram.values("user_id"))
        if self.value() == "blocked":
            return queryset.filter(
                pk__in=telegram.filter(blocked_at__isnull=False).values("user_id")
            )
        return queryset


class SocialAccountInline(admin.TabularInline):
    model = SocialAccount
    extra = 0
    fields = ("provider", "uid", "email", "notify", "blocked_at", "created_at", "last_login_at")
    readonly_fields = fields
    can_delete = True
    show_change_link = False

    def has_add_permission(self, request: HttpRequest, obj: User | None = None) -> bool:
        return False


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = (
        "phone",
        "first_name",
        "last_name",
        "show_roles",
        "audience",
        "is_active",
        "date_joined",
    )
    list_filter = (RoleFilter, CourseFilter, TelegramFilter, "audience", "is_active", "is_staff")
    search_fields = ("phone", "first_name", "last_name")
    ordering = ("-date_joined",)
    # Rozilikni faqat foydalanuvchining o'zi beradi yoki qaytarib oladi (kabinet sozlamalari).
    readonly_fields = (
        "last_login",
        "date_joined",
        "terms_accepted_at",
        "terms_version",
        "marketing_consent_at",
        "referral_code",
        "referred_by",
        "show_referrals",
    )

    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("phone", "password1", "password2")}),)
    inlines = [SocialAccountInline]

    def get_queryset(self, request: HttpRequest) -> QuerySet[User]:
        return super().get_queryset(request).prefetch_related("groups")

    def get_fieldsets(self, request: HttpRequest, obj: Any = None) -> Any:
        if obj is None:
            return self.add_fieldsets
        # Rollar — faqat Admin'ga; superuser belgisi va alohida ruxsatlar — faqat superuser'ga.
        # Guruhlar maydoni ko'rsatilmaydi: rollar orqali boshqariladi (`set_roles`).
        access: list[str] = ["is_active"]
        if can_manage_roles(request.user):
            access.append("roles")
        if request.user.is_superuser:
            access += ["is_superuser", "user_permissions"]
        return (
            (None, {"fields": ("phone", "password")}),
            (
                _("Shaxsiy ma'lumotlar"),
                {"fields": ("first_name", "last_name", "avatar", "locale", "audience")},
            ),
            (
                _("Rozilik"),
                {"fields": ("terms_accepted_at", "terms_version", "marketing_consent_at")},
            ),
            (_("Kirish va rollar"), {"fields": access}),
            (
                _("Do'stni taklif qilish"),
                {"fields": ("referral_code", "referred_by", "show_referrals")},
            ),
            (_("Sanalar"), {"fields": ("last_login", "date_joined")}),
        )

    def get_form(
        self, request: HttpRequest, obj: Any = None, change: bool = False, **kwargs: Any
    ) -> Any:
        form = super().get_form(request, obj, change=change, **kwargs)
        # E'lon qilingan maydon fieldsets'dan qat'i nazar formada qoladi — Admin bo'lmasa olinadi.
        if not can_manage_roles(request.user):
            form.base_fields.pop("roles", None)
        return form

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if not super().has_change_permission(request, obj):
            return False
        # Menejer o'quvchilar akkauntini o'zgartiradi, xodimlarnikini — yo'q (faqat ko'radi).
        if obj is not None and (obj.is_staff or obj.is_superuser):
            return can_manage_roles(request.user)
        return True

    def save_related(self, request: HttpRequest, form: Any, formsets: Any, change: bool) -> None:
        super().save_related(request, form, formsets, change)
        if "roles" in form.cleaned_data and can_manage_roles(request.user):
            set_roles(form.instance, form.cleaned_data["roles"])

    @admin.display(description=_("Taklif qilganlari"))
    def show_referrals(self, obj: User) -> int:
        return obj.referrals.count()

    @admin.display(description=_("Rollar"))
    def show_roles(self, obj: User) -> str:
        names = role_names(obj)
        return ", ".join(str(Role(name).label) for name in Role.values if name in names) or "—"


admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(OneTimeCode)
class OneTimeCodeAdmin(ModelAdmin):
    """SMS kodlar jurnali: qo'llab-quvvatlash uchun ("kod keldimi?"). Kodning o'zi saqlanmaydi."""

    list_display = ("phone", "purpose", "created_at", "expires_at", "used_at", "attempts", "ip")
    list_filter = ("purpose", "created_at")
    search_fields = ("phone",)
    date_hierarchy = "created_at"
    exclude = ("code_hash",)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: OneTimeCode | None = None) -> bool:
        return False
