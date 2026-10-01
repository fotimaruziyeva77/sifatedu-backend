"""Admin bosh sahifasi (Unfold `DASHBOARD_CALLBACK`): statistika faqat ruxsati borlarga."""

import json
from datetime import timedelta
from typing import Any

from django.http import HttpRequest
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.utils.translation import gettext as _

from apps.users.models import User

from . import metrics

PERMISSION = "stats.view_statistics"


def number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def som(amount: int) -> str:
    return number(amount) + " so'm"


def card(
    title: str, value: int, previous: int, note: str, icon: str, url: str = ""
) -> dict[str, Any]:
    delta = value - previous
    return {
        "title": title,
        "value": value,
        "previous": previous,
        "delta": delta,
        "trend": "up" if delta > 0 else "down" if delta < 0 else "flat",
        "note": note,
        "icon": icon,
        "url": url,
    }


def users_link(viewer: User, p: metrics.Period, **extra: str) -> str:
    return metrics.admin_link(
        viewer,
        "users.user",
        date_joined__date__gte=timezone.localdate(p.start).isoformat(),
        date_joined__date__lt=timezone.localdate(p.end).isoformat(),
        **extra,
    )


def chart(series: dict[str, list[Any]]) -> str:
    """Unfold bar chart (Chart.js) ma'lumoti. Sana qisqa (`29.09`): 30 ta yorliq sig'sin."""
    bar = {"borderRadius": 4, "maxBarThickness": 14}
    return json.dumps(
        {
            "labels": [f"{day:%d.%m}" for day in series["dates"]],
            "datasets": [
                {
                    "label": _("Ro'yxatdan o'tdi"),
                    "data": series["registered"],
                    "backgroundColor": "var(--color-base-300)",
                    **bar,
                },
                {
                    "label": _("To'ladi"),
                    "data": series["paid"],
                    "backgroundColor": "var(--color-primary-600)",
                    **bar,
                },
            ],
        }
    )


def build(viewer: User, key: str) -> dict[str, Any]:
    p = metrics.period(key)
    now, before = metrics.summary(p), metrics.summary(p.previous)
    people = metrics.audience(p)
    no_course, no_course_total = metrics.without_course(p)
    expired, expired_total = metrics.expired_access()
    cards = [
        card(
            _("Ro'yxatdan o'tdi"),
            now.registered,
            before.registered,
            _("Jami: %(total)s · Kids: %(kids)s · Telegram orqali: %(telegram)s")
            % {"total": number(people.students), "kids": now.kids, "telegram": now.via_telegram},
            "person_add",
            users_link(viewer, p),
        ),
        card(
            _("Kurs tanladi"),
            now.chose_course,
            before.chose_course,
            _("Yozildi: %(enrolled)s · to'lovni boshladi: %(started)s")
            % {"enrolled": now.enrolled, "started": now.started_payment},
            "school",
        ),
        card(
            _("To'ladi"),
            now.paid,
            before.paid,
            som(now.revenue),
            "payments",
            metrics.admin_link(viewer, "payments.order", status__exact="PAID"),
        ),
        card(
            _("Arizalar"),
            now.leads,
            before.leads,
            _("AI orqali: %(ai)s") % {"ai": now.leads_ai},
            "contact_phone",
            metrics.admin_link(viewer, "leads.lead"),
        ),
        card(
            _("AI suhbatlar"),
            now.conversations,
            before.conversations,
            _("Xarajat: $%(cost)s") % {"cost": f"{now.ai_cost:.2f}"},
            "smart_toy",
            metrics.admin_link(viewer, "assistant.conversation"),
        ),
        card(
            _("Botga qo'shildi"),
            people.bot_new,
            metrics.bot_joined(p.previous),
            _("Jami: %(total)s · ro'yxatdan o'tmagan: %(guests)s · bloklagan: %(blocked)s")
            % {
                "total": number(people.bot),
                "guests": number(people.bot - people.bot_registered),
                "blocked": number(people.bot_blocked),
            },
            "send",
            metrics.admin_link(viewer, "bot.botchat"),
        ),
    ]
    week_ago = timezone.localdate() - timedelta(days=7)
    return {
        "period": p,
        "periods": [(code, str(label)) for code, label in metrics.PERIODS.items()],
        "cards": cards,
        "funnel": metrics.funnel(p),
        "chart": chart(metrics.daily_series()),
        "problems": metrics.problems(p, viewer),
        "no_course": no_course,
        "no_course_total": no_course_total,
        "no_course_url": users_link(viewer, p, course="none"),
        "expired": expired,
        "expired_total": expired_total,
        "expired_url": metrics.admin_link(
            viewer,
            "learning.enrollment",
            study_format__exact="OFFLINE",
            expires_at__date__gte=week_ago.isoformat(),
            expires_at__date__lt=(timezone.localdate() + timedelta(days=1)).isoformat(),
        ),
        "can_open_users": viewer.has_perm("users.view_user"),
        "index_url": reverse("admin:index"),
    }


def dashboard_callback(request: HttpRequest, context: dict[str, Any]) -> dict[str, Any]:
    user = request.user
    if not isinstance(user, User) or not user.has_perm(PERMISSION):
        return context
    context["stats"] = build(user, request.GET.get("period", "today"))
    context["period_query"] = urlencode({"period": context["stats"]["period"].key})
    return context
