"""Bot menyusi: kurslarim, testlar, jadval, do'stni taklif qilish, sozlamalar.

Saytga olib boradigan tugmalar bir martalik kirish havolasi bilan (`links.login_url`): o'quvchi
parol yozmasdan kerakli sahifaga tushadi.
"""

from typing import Any
from urllib.parse import urlencode

from django.utils import timezone

from apps.learning import access
from apps.learning.models import Enrollment
from apps.learning.views import completed_ids, course_card, with_program
from apps.live import services as live
from apps.live.models import LiveLesson
from apps.notifications.texts import day_month
from apps.rewards.models import GameSettings
from apps.users import services as user_services
from apps.users.models import User

from . import daily, exam, links
from .models import BotChat
from .quiz import available
from .send import Rows, button, escape, link, send
from .texts import LANGUAGES, t

MAX_LESSONS = 8
MAX_QUIZZES = 8


def main_keyboard(
    locale: str, *, registered: bool, admin: bool = False, newcomer: bool = False
) -> dict[str, Any]:
    """Pastki menyu. Ro'yxatdan o'tmaganda — telefon yuborish tugmasi; statistikani ko'rish
    huquqi borga — eng tepada «Admin panel»; hali kursga yozilmaganga — «Daraja testi»."""
    rows: list[list[dict[str, Any]]]
    if registered:
        rows = [[{"text": t(locale, "btn_admin")}]] if admin else []
        if newcomer:
            rows.append([{"text": t(locale, "btn_placement")}])
        rows += [
            [{"text": t(locale, "btn_today")}],
            [{"text": t(locale, "btn_courses")}, {"text": t(locale, "btn_tests")}],
            [{"text": t(locale, "btn_schedule")}, {"text": t(locale, "btn_invite")}],
            [{"text": t(locale, "btn_ask")}, {"text": t(locale, "btn_settings")}],
        ]
    else:
        rows = [
            [{"text": t(locale, "btn_contact"), "request_contact": True}],
            [{"text": t(locale, "btn_ask")}, {"text": t(locale, "btn_settings")}],
        ]
    return {"keyboard": rows, "resize_keyboard": True, "is_persistent": True}


def courses(chat: BotChat, user: User) -> None:
    locale = chat.language
    items = list(with_program(access.enrolled_courses(user)).order_by("order", "id"))
    if not items:
        catalog = link(t(locale, "btn_catalog"), links.site_url("/courses", locale))
        send(chat.chat_id, t(locale, "no_courses"), [[catalog]])
        return
    enrollments = {item.course_id: item for item in Enrollment.objects.filter(user=user)}
    blocks = [t(locale, "courses_title")]
    rows: Rows = []
    for course in items:
        card = course_card(
            course,
            completed_ids(user, course),
            enrollments.get(course.pk),
            access.quiz_gate(user, course.pk),
        )
        lessons = {
            lesson.pk: lesson for module in course.modules.all() for lesson in module.lessons.all()
        }
        title = escape(course.title)
        total, done = card["lesson_count"], card["completed_count"]
        upcoming = lessons.get(card["next_lesson_id"])
        if total and done >= total:
            blocks.append(t(locale, "course_done", title=title))
        else:
            blocks.append(
                t(
                    locale,
                    "course_line",
                    title=title,
                    percent=card["percent"],
                    done=done,
                    total=total,
                    lesson=escape(upcoming.title) if upcoming else "—",
                )
            )
        if upcoming is not None:
            path = f"/dashboard/courses/{course.slug}/lessons/{upcoming.pk}"
            rows.append([link(f"▶️ {str(course.title)[:48]}", links.login_url(user, path, chat))])
    send(chat.chat_id, "\n\n".join(blocks), rows)


def tests(chat: BotChat, user: User) -> None:
    locale = chat.language
    found, passed = available(user)
    blocks = [t(locale, "tests_title")]
    rows: Rows = []
    # Bugungi kunlik test (guruh o'quvchisiga) — eng tepada.
    today_test = daily.menu_block(user, locale)
    if today_test is not None:
        text, buttons = today_test
        blocks.append(text)
        rows += buttons
    # Oylik imtihon ochiq bo'lsa — undan keyin.
    for opened in exam.open_exams(user):
        title = exam.course_title(opened, locale)
        blocks.append(t(locale, "tests_exam", course=escape(title)))
        rows.append([button(t(locale, "btn_exam", course=title[:40]), f"xs:{opened.pk}")])
    if found:
        lines = [t(locale, "tests_open")]
        for item in found[:MAX_QUIZZES]:
            lesson = item.quiz.lesson
            lines.append(
                t(
                    locale,
                    "tests_line",
                    lesson=escape(lesson.title),
                    course=escape(item.course_title),
                )
            )
            label = f"{'▶️' if item.in_progress else '📝'} {str(lesson.title)[:48]}"
            rows.append([button(label, f"qs:{item.quiz.pk}")])
        blocks.append("\n".join(lines))
    else:
        blocks.append(t(locale, "tests_empty"))
    if passed:
        blocks.append(t(locale, "tests_passed", count=passed))
    send(chat.chat_id, "\n\n".join(blocks), rows)


def place(lesson: LiveLesson, locale: str) -> str:
    if lesson.kind == LiveLesson.Kind.ONLINE:
        return t(locale, "place_online")
    if lesson.room:
        return t(locale, "place_room", room=escape(lesson.room))
    return t(locale, "place_offline")


def schedule(chat: BotChat, user: User) -> None:
    locale = chat.language
    if not live.has_schedule(user):
        send(chat.chat_id, t(locale, "schedule_no_group"))
        return
    lessons = live.lessons_for(user, upcoming=True)[:MAX_LESSONS]
    if not lessons:
        send(chat.chat_id, t(locale, "schedule_empty"))
        return
    now = timezone.now()
    blocks = [t(locale, "schedule_title")]
    rows: Rows = []
    waiting = False
    for lesson in lessons:
        starts = timezone.localtime(lesson.starts_at)
        ends = timezone.localtime(lesson.ends_at)
        when = f"{day_month(starts.date(), locale)}, {starts:%H:%M}–{ends:%H:%M}"
        block = t(
            locale,
            "schedule_line",
            when=when,
            course=escape(lesson.group.course.title),
            group=escape(lesson.group.name),
            place=place(lesson, locale),
        )
        topic = lesson.title or (str(lesson.topic.title) if lesson.topic else "")
        if topic:
            block += "\n" + t(locale, "schedule_topic", topic=escape(topic))
        if lesson.is_canceled:
            reason = escape(lesson.cancel_reason) if lesson.cancel_reason else "—"
            block += "\n" + t(locale, "schedule_canceled", reason=reason)
        blocks.append(block)
        online = lesson.kind == LiveLesson.Kind.ONLINE and bool(lesson.meet_url)
        if online and not lesson.is_canceled:
            if lesson.opens_at <= now < lesson.ends_at:
                url = links.login_url(user, f"/api/v1/live/{lesson.pk}/join/", chat)
                rows.append([link(t(locale, "btn_join", time=f"{starts:%H:%M}"), url)])
            else:
                waiting = True
    if waiting:
        blocks.append(t(locale, "schedule_join_hint"))
    send(chat.chat_id, "\n\n".join(blocks), rows)


def invite_rewards(locale: str) -> list[str]:
    """Taklif mukofotlari — o'yin sozlamalaridagi qiymatlar (0 bo'lsa, o'sha qator yo'q)."""
    config = GameSettings.load()
    lines = []
    if config.referral_lesson_coins:
        lines.append(t(locale, "invite_lesson", coins=config.referral_lesson_coins))
    paid = []
    if config.referral_paid_coins:
        paid.append(t(locale, "invite_coins", coins=config.referral_paid_coins))
    if config.coupon_percent:
        paid.append(t(locale, "invite_coupon", percent=config.coupon_percent))
    if paid:
        lines.append(t(locale, "invite_paid", reward=t(locale, "invite_and").join(paid)))
    if config.referral_discount:
        lines.append(t(locale, "invite_discount", percent=config.referral_discount))
    return lines


def invite(chat: BotChat, user: User) -> None:
    locale = chat.language
    code = user_services.referral_code(user)
    bot = links.bot_url(links.REFERRAL_PREFIX + code) or ""
    site = f"{links.base_url()}/{locale}?{urlencode({'ref': code})}"
    text = t(
        locale,
        "invite",
        bot=escape(bot or "—"),
        site=escape(site),
        count=user.referrals.count(),
    )
    rewards = invite_rewards(locale)
    if rewards:
        text += "\n\n" + "\n".join([t(locale, "invite_rewards"), *rewards])
    share = "https://t.me/share/url?" + urlencode(
        {"url": bot or site, "text": t(locale, "share_text")}
    )
    send(chat.chat_id, text, [[link(t(locale, "btn_share"), share)]])


def settings_view(chat: BotChat, user: User | None) -> tuple[str, Rows]:
    locale = chat.language
    text = t(
        locale,
        "settings",
        language=LANGUAGES.get(locale, LANGUAGES["uz"]),
        news=t(locale, "news_on" if chat.news else "news_off"),
    )
    rows: Rows = [
        [button(t(locale, "btn_language"), "lang")],
        [button(t(locale, "btn_news_off" if chat.news else "btn_news_on"), "news")],
    ]
    if user is not None:
        rows.append([link(t(locale, "btn_site"), links.login_url(user, "/dashboard", chat))])
    return text, rows


def settings(chat: BotChat, user: User | None) -> None:
    text, rows = settings_view(chat, user)
    send(chat.chat_id, text, rows)
