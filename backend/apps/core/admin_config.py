"""Unfold admin uchun callback'lar: muhit belgisi, menyudagi sonlar va havolalar."""

from django.conf import settings
from django.http import HttpRequest


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
