"""Botdagi admin panel (/admin yoki «📊 Admin panel» tugmasi): foydalanuvchilar, o'qish, savdo
va muammolar. Raqamlar admin bosh sahifasidagi bilan bir manbadan (`apps.stats.metrics`).

Faqat statistikani ko'rish huquqi borlarga (direktor, admin, menejer) — Telegram'i shu akkauntga
ulangan bo'lsa. Davr tugmalari xabarni joyida yangilaydi; huquq har bosishda qayta tekshiriladi.
"""

from django.urls import reverse
from django.utils import timezone

from apps.notifications.texts import day_month
from apps.stats import metrics
from apps.stats.dashboard import PERMISSION, number
from apps.users.models import User

from . import links
from .models import BotChat
from .send import Rows, button, edit, escape, link, send
from .texts import t

PERIODS = ("today", "yesterday", "7d", "30d")
MAX_PROBLEMS = 8
BROADCAST_PERMISSION = "notifications.add_broadcast"


def allowed(user: User | None) -> bool:
    return user is not None and user.has_perm(PERMISSION)


def branch(lines: list[str]) -> list[str]:
    """Bo'lim qatorlari daraxt ko'rinishida (├ … └)."""
    last = len(lines) - 1
    return [f"{'└' if index == last else '├'} {line}" for index, line in enumerate(lines)]


def heading(p: metrics.Period, locale: str) -> str:
    """«Bugun, 1-oktabr» yoki «7 kun: 25-sentabr – 1-oktabr»."""
    label = t(locale, f"period_{p.key}")
    days = p.days
    if len(days) == 1:
        return f"{label}, {day_month(days[0], locale)}"
    return f"{label}: {day_month(days[0], locale)} – {day_month(days[-1], locale)}"


def render(p: metrics.Period, locale: str) -> str:
    people = metrics.audience(p)
    study = metrics.learning(p)
    sales = metrics.summary(p)
    found = metrics.problems(p)

    def say(key: str, **values: object) -> str:
        return t(locale, key, **values)

    lines = [say("admin_title", period=escape(heading(p, locale))), "", say("admin_users")]
    lines.append(say("admin_bot", total=number(people.bot), new=number(people.bot_new)))
    lines += branch(
        [
            say("admin_bot_registered", count=number(people.bot_registered)),
            say("admin_bot_guests", count=number(people.bot - people.bot_registered)),
            say("admin_bot_blocked", count=number(people.bot_blocked)),
            say("admin_bot_muted", count=number(people.bot_muted)),
        ]
    )
    lines.append(say("admin_site", total=number(people.students), new=number(people.students_new)))
    lines += branch(
        [
            say("admin_site_telegram", count=number(people.telegram)),
            say("admin_site_kids", count=number(people.kids)),
        ]
    )
    lines += ["", say("admin_learning")]
    lines += branch(
        [
            say("admin_lessons", count=number(study.lessons)),
            say("admin_quizzes", count=number(study.quizzes)),
            say("admin_learners", count=number(study.learners)),
            say("admin_homework", count=number(study.homework)),
        ]
    )
    lines += ["", say("admin_sales")]
    lines += branch(
        [
            say("admin_chose", count=number(sales.chose_course)),
            say(
                "admin_paid",
                count=number(sales.paid),
                amount=say("admin_money", amount=number(sales.revenue)),
            ),
            say("admin_leads", count=number(sales.leads), ai=number(sales.leads_ai)),
            say("admin_ai", count=number(sales.conversations), cost=f"{sales.ai_cost:.2f}"),
        ]
    )
    lines.append("")
    if found:
        lines.append(say("admin_problems"))
        lines += [
            f"• {escape(problem.title)} — {number(problem.count)}"
            for problem in found[:MAX_PROBLEMS]
        ]
    else:
        lines.append(say("admin_no_problems"))
    lines += ["", say("admin_updated", time=f"{timezone.localtime():%H:%M}")]
    return "\n".join(lines)


def buttons(p: metrics.Period, user: User, locale: str) -> Rows:
    periods = [
        button(("✅ " if key == p.key else "") + t(locale, f"period_{key}"), f"ad:{key}")
        for key in PERIODS
    ]
    rows: Rows = [
        periods,
        [button(t(locale, "admin_refresh"), f"ad:{p.key}")],
        [link(t(locale, "admin_open_site"), links.base_url() + reverse("admin:index"))],
    ]
    if user.has_perm(BROADCAST_PERMISSION):
        url = links.base_url() + reverse("admin:notifications_broadcast_add")
        rows.append([link(t(locale, "admin_broadcast"), url)])
    return rows


def show(chat: BotChat, user: User | None) -> None:
    """/admin yoki menyu tugmasi: bugungi statistika."""
    locale = chat.language
    if user is None or not allowed(user):
        send(chat.chat_id, t(locale, "admin_denied"))
        return
    p = metrics.period("today")
    send(chat.chat_id, render(p, locale), buttons(p, user, locale))


def on_button(chat: BotChat, user: User | None, args: list[str], message_id: int | None) -> str:
    """Davr yoki «Yangilash» tugmasi: xabar joyida yangilanadi. Qaytadi: ogohlantirish."""
    locale = chat.language
    if user is None or not allowed(user):
        return t(locale, "admin_denied")
    p = metrics.period(args[0] if args else "today")
    edit(chat.chat_id, message_id, render(p, locale), buttons(p, user, locale))
    return ""
