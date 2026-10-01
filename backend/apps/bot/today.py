"""✅ Bugungi topshiriqlar: kunlik 3 ta topshiriq botda (XP va reyting — faqat saytda).

Har topshiriq yonida tugma: dars va vazifa — saytga (bir martalik kirish havolasi), test va
takrorlash — botning o'zida, jonli dars — jadvalga. Ertalab 09:00 da shu ro'yxat xabar bo'lib
keladi.
"""

from apps.rewards import daily
from apps.rewards.models import DailyTask
from apps.users.models import User

from . import links
from .models import BotChat
from .send import Rows, button, escape, link, send
from .texts import t

Kind = DailyTask.Kind
MARKS = {True: "✅", False: "⬜"}


def label(task: DailyTask, locale: str) -> str:
    title = escape(task.title)
    return t(locale, f"today_{task.kind.lower()}", title=title)


def action(task: DailyTask, chat: BotChat, user: User) -> dict | None:
    locale = chat.language
    if task.done_at is not None:
        return None
    if task.kind == Kind.QUIZ and task.quiz_id:
        return button(t(locale, "btn_today_quiz"), f"qs:{task.quiz_id}")
    if task.kind == Kind.REVIEW:
        return button(t(locale, "btn_today_review"), "rv")
    if task.kind in (Kind.LESSON, Kind.HOMEWORK) and task.lesson_id and task.course is not None:
        path = f"/dashboard/courses/{task.course.slug}/lessons/{task.lesson_id}"
        if task.kind == Kind.HOMEWORK:
            path += "#homework"
        key = "btn_today_lesson" if task.kind == Kind.LESSON else "btn_today_homework"
        return link(t(locale, key), links.login_url(user, path, chat))
    if task.kind == Kind.LIVE:
        return link(t(locale, "btn_today_live"), links.login_url(user, "/dashboard/schedule", chat))
    return None


def view(chat: BotChat, user: User) -> tuple[str, Rows]:
    locale = chat.language
    tasks = daily.today(user)
    if not tasks:
        return t(locale, "today_empty"), []
    lines = [t(locale, "today_title")]
    for index, task in enumerate(tasks, 1):
        lines.append(f"{MARKS[task.done_at is not None]} {index}. {label(task, locale)}")
    rows: Rows = []
    for task in tasks:
        found = action(task, chat, user)
        if found is not None:
            rows.append([found])
    if all(task.done_at is not None for task in tasks):
        lines.append("\n" + t(locale, "today_done"))
    return "\n".join(lines), rows


def show(chat: BotChat, user: User) -> None:
    text, rows = view(chat, user)
    send(chat.chat_id, text, rows)


def morning(chat: BotChat, user: User) -> bool:
    """09:00 dagi xabar. Topshiriq bo'lmasa — yuborilmaydi."""
    text, rows = view(chat, user)
    if not daily.today(user):
        return False
    send(chat.chat_id, f"{t(chat.language, 'today_morning')}\n\n{text}", rows)
    return True
