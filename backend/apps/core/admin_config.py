"""Unfold admin uchun callback'lar: muhit belgisi, menyudagi sonlar va havolalar."""

from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django.templatetags.static import static

from apps.tenancy.sites import center_name, is_flagship


def site_title(request: HttpRequest) -> str:
    return center_name()


def site_logo(request: HttpRequest) -> dict[str, str] | None:
    """Markaz logosi; bo'lmasa panelda nomi ko'rinadi. Birinchi markazda — o'z vektor logolari."""
    if is_flagship():
        return {"light": static("brand/logo-light.svg"), "dark": static("brand/logo-dark.svg")}
    from apps.content.models import SiteSettings

    site = SiteSettings.load()
    if not site.logo:
        return None
    light = site.logo.url
    return {"light": light, "dark": site.logo_dark.url if site.logo_dark else light}


def site_favicons(request: HttpRequest) -> list[dict[str, Any]]:
    if is_flagship():
        return [{"rel": "icon", "type": "image/svg+xml", "href": static("brand/icon.svg")}]
    return []


def environment_callback(request: HttpRequest) -> list[str] | None:
    if settings.DEBUG:
        return ["Development", "warning"]
    return None


def new_leads_badge(request: HttpRequest) -> str | None:
    """Menyuda ko'rib chiqilmagan arizalar soni."""
    from apps.leads.models import Lead

    count = Lead.objects.filter(status=Lead.Status.NEW).count()
    return str(count) if count else None


def manager_needed_badge(request: HttpRequest) -> str | None:
    """AI suhbatlardan menejer aralashuvini kutayotganlari."""
    from apps.assistant.models import Conversation

    count = Conversation.objects.filter(status=Conversation.Status.MANAGER).count()
    return str(count) if count else None


def count_badge(count: int) -> str | None:
    return str(count) if count else None


def homework_badge(request: HttpRequest) -> str | None:
    """Tekshirilishi kutilayotgan uy vazifalari — shu xodim tekshira oladiganlari."""
    from apps.homework.models import Submission
    from apps.homework.services import reviewable

    return count_badge(reviewable(request.user).filter(status=Submission.Status.SUBMITTED).count())


def exam_grading_badge(request: HttpRequest) -> str | None:
    """Baholanmagan imtihon javoblari — shu xodim baholaydiganlari."""
    from apps.exams.services import pending_for

    return count_badge(pending_for(request.user).count())


def shop_badge(request: HttpRequest) -> str | None:
    """Do'kondagi yangi (hali tayyorlanmagan) buyurtmalar."""
    from apps.shop.models import Purchase

    return count_badge(Purchase.objects.filter(status=Purchase.Status.NEW).count())


def refunds_badge(request: HttpRequest) -> str | None:
    """Ko'rib chiqilmagan pul qaytarish so'rovlari."""
    from apps.payments.models import Refund

    return count_badge(Refund.objects.filter(status=Refund.Status.REQUESTED).count())


def cabinet_permission(request: HttpRequest) -> bool:
    """Saytdagi guruhlar kabineti: o'qituvchi, admin va menejer (direktor — faqat statistika)."""
    from apps.users.roles import Role, has_role, manages_groups

    return has_role(request.user, Role.TEACHER) or manages_groups(request.user)


def cabinet_link(request: HttpRequest) -> str:
    """Kabinetdagi guruhlar sahifasi foydalanuvchi tilida (sayt bilan bir domen)."""
    from apps.notifications.texts import locale_of

    return f"/{locale_of(getattr(request.user, 'locale', ''))}/dashboard/teaching"
