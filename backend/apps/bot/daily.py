"""Kunlik test botda: 07:00 dagi xabardagi tugma yoki «📝 Testlar» → savollar → oxirida nechta
to'g'ri va noto'g'ri, XP va coin, guruhdagi o'rin. To'g'ri javoblar va izohlar 23:00 dan keyin.
Urinish sayt bilan bitta: saytda boshlangan test botda davom etadi va aksincha.

Tugmalar dars testiniki (qa/qt/qd/qo/qm/qr); holat — `BotChat.state["quiz"]` (`"k": "daily"`).
Javobdan keyin to'g'ri/noto'g'ri aytilmaydi — natija oxirida.
"""

from typing import Any

from django.utils import timezone

from apps.dailytest import services
from apps.dailytest.models import DailyAttempt, DailyTest
from apps.quizzes.models import Question
from apps.quizzes.services import Layout
from apps.rewards import services as rewards
from apps.users.models import User

from . import links
from .models import BotChat
from .quiz import (
    Kind,
    forget,
    interpret,
    parse_button,
    redraw,
    render,
    review_blocks,
    save_state,
    short_answer,
)
from .send import Rows, button, edit, escape, link, send, split
from .texts import t

DAILY = "daily"


def until(test: DailyTest) -> str:
    return f"{timezone.localtime(test.closes_at):%H:%M}"


def entry(chat: BotChat, user: User) -> None:
    """Bugungi test: ishlanmagan bo'lsa — shartlar va «Boshlash», boshlangan bo'lsa — davomi,
    tugatilgan bo'lsa — natija."""
    locale = chat.language
    test = services.today_for(user)
    if test is None:
        send(chat.chat_id, t(locale, "daily_none"))
        return
    attempt = DailyAttempt.objects.filter(test=test, student=user).first()
    if attempt is not None and attempt.finished_at is None and services.is_open(test):
        advance(chat, user, attempt)
        return
    if attempt is not None:
        if attempt.finished_at is None:
            services.finish(attempt)
        send(
            chat.chat_id,
            t(locale, "daily_already", correct=attempt.correct, total=attempt.total),
            result_rows(attempt, locale),
        )
        return
    if not services.is_open(test):
        send(chat.chat_id, t(locale, "daily_closed"))
        return
    config = rewards.settings()
    text = t(
        locale,
        "daily_intro",
        group=escape(test.group.name),
        count=test.questions_count,
        until=until(test),
        xp=config.daily_test_xp,
        coins=config.daily_test_coins,
    )
    send(chat.chat_id, text, [[button(t(locale, "btn_daily_start"), f"dg:{test.pk}")]])


def start(chat: BotChat, user: User, test_id: int) -> None:
    test = DailyTest.objects.select_related("group").filter(pk=test_id).first()
    if test is None:
        send(chat.chat_id, t(chat.language, "daily_none"))
        return
    try:
        attempt = services.start(test, user)
    except services.DailyTestError as exc:
        send(chat.chat_id, escape(str(exc)))
        return
    advance(chat, user, attempt)


def advance(chat: BotChat, user: User, attempt: DailyAttempt) -> None:
    """Keyingi savol yoki (savol qolmagan / test yopilgan bo'lsa) natija."""
    test = attempt.test
    step = services.current(attempt) if services.is_open(test) else None
    if attempt.finished_at is not None or step is None:
        finish(chat, user, attempt)
        return
    index, total, question = step
    layout = Layout.build(question, attempt.seed)
    state: dict[str, Any] = {
        "k": DAILY,
        "a": attempt.pk,
        "q": question.pk,
        "i": index,
        "n": total,
        "sel": [],
    }
    body, hint, rows = render(layout, state, chat.language)
    message = send(chat.chat_id, f"{body}\n\n{hint}", rows)
    state["m"] = message.get("message_id")
    chat.state["quiz"] = state
    if question.kind == Kind.TEXT:
        chat.state["await"] = "text"
    else:
        chat.state.pop("await", None)
    save_state(chat)


def submit(
    chat: BotChat,
    user: User,
    attempt: DailyAttempt,
    layout: Layout,
    response: dict[str, Any],
) -> None:
    locale = chat.language
    state = dict(chat.state.get("quiz") or {})
    try:
        services.answer(attempt, layout.question.pk, response)
    except services.DailyTestError as exc:
        forget(chat)
        save_state(chat)
        send(chat.chat_id, escape(str(exc)))
        # Saytda javob berilgan yoki test yopilgan: keyingi javobsiz savol (yoki natija).
        advance(chat, user, attempt)
        return
    body, _hint, _rows = render(layout, {**state, "sel": []}, locale)
    yours = t(locale, "q_your", answer=short_answer(layout, response))
    edit(chat.chat_id, state.get("m"), f"{body}\n\n{yours}\n{t(locale, 'exam_saved')}")
    forget(chat)
    advance(chat, user, attempt)


def result_rows(attempt: DailyAttempt, locale: str) -> Rows:
    rows: Rows = [[button(t(locale, "btn_daily_rating"), f"dr:{attempt.test_id}")]]
    if services.can_review(attempt):
        rows.append([button(t(locale, "btn_daily_review"), f"dv:{attempt.pk}")])
    return rows


def finish(chat: BotChat, user: User, attempt: DailyAttempt) -> None:
    result = services.finish(attempt)
    forget(chat)
    save_state(chat)
    locale = chat.language
    reward = (
        t(locale, "daily_reward", xp=result.xp, coins=result.coins)
        if result.xp or result.coins
        else ""
    )
    text = t(
        locale,
        "daily_done",
        correct=result.correct,
        wrong=result.wrong,
        reward=reward,
        place=result.place,
        people=result.people,
        until=until(attempt.test),
    )
    send(chat.chat_id, text, result_rows(attempt, locale))


def rating(chat: BotChat, user: User, test_id: int) -> None:
    """Guruh reytingi: bugungi (eng yaxshi 10 ta) va haftalik."""
    locale = chat.language
    test = DailyTest.objects.select_related("group").filter(pk=test_id).first()
    if test is None or not services.is_member(test, user):
        send(chat.chat_id, t(locale, "daily_none"))
        return
    blocks = [t(locale, "daily_rating_title", group=escape(test.group.name))]
    for title_key, rows in (
        ("daily_rating_day", services.day_rating(test)),
        ("daily_rating_week", services.week_rating(test.group, test.day)),
    ):
        lines = [t(locale, title_key)]
        if not rows:
            lines.append(t(locale, "daily_rating_empty"))
        for index, row in enumerate(rows[: services.TOP], 1):
            mark = " ←" if row.student_id == user.pk else ""
            lines.append(f"{index}. {escape(row.name)} — {row.correct}/{row.total}{mark}")
        mine = next((index for index, row in enumerate(rows, 1) if row.student_id == user.pk), 0)
        if mine > services.TOP:
            lines.append(t(locale, "daily_rating_you", place=mine))
        blocks.append("\n".join(lines))
    send(chat.chat_id, "\n\n".join(blocks))


def review(chat: BotChat, user: User, attempt_id: int) -> None:
    """Test yopilgach: xatolar — savol, javobingiz, to'g'ri javob va izoh."""
    locale = chat.language
    attempt = (
        DailyAttempt.objects.select_related("test").filter(pk=attempt_id, student=user).first()
    )
    if attempt is None:
        send(chat.chat_id, t(locale, "daily_none"))
        return
    if not services.can_review(attempt):
        send(chat.chat_id, t(locale, "daily_review_wait", until=until(attempt.test)))
        return
    blocks = review_blocks(attempt, services.review(attempt), locale)
    for text in split(blocks):
        send(chat.chat_id, text)


def load(chat: BotChat, user: User) -> tuple[DailyAttempt, Question, Layout] | None:
    state = chat.state.get("quiz") or {}
    attempt_id, question_id = state.get("a"), state.get("q")
    if not isinstance(attempt_id, int) or not isinstance(question_id, int):
        return None
    attempt = (
        DailyAttempt.objects.select_related("test")
        .filter(pk=attempt_id, student=user, finished_at__isnull=True)
        .first()
    )
    question = Question.objects.prefetch_related("choices").filter(pk=question_id).first()
    if attempt is None or question is None:
        return None
    return attempt, question, Layout.build(question, attempt.seed)


def on_button(chat: BotChat, user: User, action: str, args: list[str]) -> str:
    """Kunlik test savoli tugmasi. Qaytadi: qisqa ogohlantirish yoki bo'sh qator."""
    locale = chat.language
    parsed = parse_button(args)
    if parsed is None:
        return ""
    attempt_id, question_id, position = parsed
    state = dict(chat.state.get("quiz") or {})
    if state.get("a") != attempt_id or state.get("q") != question_id:
        return t(locale, "q_stale")
    loaded = load(chat, user)
    if loaded is None:
        forget(chat)
        save_state(chat)
        return t(locale, "q_stale")
    attempt, question, layout = loaded
    if not services.is_open(attempt.test):
        finish(chat, user, attempt)
        return ""
    count = len(layout.shown)
    if position and not 1 <= position <= count:
        return ""
    selection = [value for value in state.get("sel") or [] if isinstance(value, int)]
    press = interpret(action, question.kind, position, selection, count, locale)
    if press.response is not None:
        submit(chat, user, attempt, layout, press.response)
    elif press.selection is not None:
        redraw(chat, layout, state, press.selection)
    return press.notice


def on_text(chat: BotChat, user: User, text: str) -> bool:
    """Yozma javob kutilayotgan kunlik test savoli bo'lsa — javob sifatida olinadi."""
    if chat.state.get("await") != "text" or not is_daily(chat):
        return False
    loaded = load(chat, user)
    if loaded is None or loaded[1].kind != Kind.TEXT:
        forget(chat)
        save_state(chat)
        return False
    attempt, _question, layout = loaded
    submit(chat, user, attempt, layout, {"text": text})
    return True


def is_daily(chat: BotChat) -> bool:
    return (chat.state.get("quiz") or {}).get("k") == DAILY


def menu_block(user: User, locale: str) -> tuple[str, Rows] | None:
    """«📝 Testlar» ro'yxati tepasida: bugungi kunlik test holati va tugmasi."""
    test = services.today_for(user)
    if test is None:
        return None
    attempt = DailyAttempt.objects.filter(test=test, student=user).first()
    if attempt is not None and attempt.finished_at is not None:
        text = t(locale, "tests_daily_done", correct=attempt.correct, total=attempt.total)
        return text, result_rows(attempt, locale)
    if not services.is_open(test):
        return None
    text = t(locale, "tests_daily", count=test.questions_count, until=until(test))
    label = t(locale, "btn_daily_continue" if attempt else "btn_daily")
    return text, [[button(label, "dq")]]


def site_link(user: User, chat: BotChat, locale: str) -> list[dict[str, Any]]:
    return [link(t(locale, "btn_daily_site"), links.login_url(user, services.LINK, chat))]
