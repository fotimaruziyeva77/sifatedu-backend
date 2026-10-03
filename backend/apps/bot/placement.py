"""Daraja testi botda: yangi kelgan odam yo'nalishni tanlaydi, vaqtli test ishlaydi, oxirida
natija, daraja va chegirma kuponi (birinchi testga), ariza esa menejerga tushadi.

Tugmalar dars testiniki (qa/qt/qd/qo/qm/qr); holat — `BotChat.state["quiz"]` (`"k": "placement"`).
Javobdan keyin to'g'ri/noto'g'ri aytilmaydi. Vaqt serverda: har savol oldidan tekshiriladi.
"""

from typing import Any

from django.utils import timezone

from apps.notifications.texts import day_month
from apps.placement import services
from apps.placement.models import PlacementAttempt, PlacementTest
from apps.quizzes.models import Question
from apps.quizzes.services import Layout
from apps.rewards import services as rewards
from apps.rewards.models import Coupon
from apps.rewards.referral import valid_coupons
from apps.users.models import User

from . import links
from .models import BotChat
from .quiz import Kind, forget, interpret, parse_button, redraw, render, save_state, short_answer
from .send import button, edit, escape, link, rows_of, send
from .texts import t

PLACEMENT = "placement"


def has_coupon(user: User) -> bool:
    return Coupon.objects.filter(user=user, kind=Coupon.Kind.PLACEMENT).exists()


def offered(user: User | None) -> bool:
    """Menyuda «🎯 Daraja testi»: hali kursga yozilmagan (bosh admin — sinab ko'rish uchun) va
    faol test bor."""
    return services.eligible(user) and bool(services.active_tests())


def allowed(chat: BotChat, user: User) -> bool:
    """Kursda o'qiyotgan (yoki xodim) eski tugma yoki menyu matni bilan kirsa — tushuntirish."""
    if services.eligible(user):
        return True
    send(chat.chat_id, t(chat.language, "placement_not_for_you"))
    return False


def choose(chat: BotChat, user: User) -> None:
    """Yo'nalishlar: har biri — daraja testi."""
    locale = chat.language
    if not allowed(chat, user):
        return
    tests = services.active_tests()
    if not tests:
        send(chat.chat_id, t(locale, "placement_none"))
        return
    config = rewards.settings()
    if has_coupon(user):
        text = t(locale, "placement_choose_again")
        active = valid_coupons(user).filter(kind=Coupon.Kind.PLACEMENT).first()
        if active is not None and active.expires_at is not None:
            text = f"{coupon_line(active, locale)}\n\n{text}"
    else:
        text = t(
            locale,
            "placement_choose",
            low=config.placement_low_coupon,
            high=config.placement_high_coupon,
            hours=config.placement_coupon_hours,
        )
    send(chat.chat_id, text, rows_of([button(test.title, f"pt:{test.pk}") for test in tests], 2))


def until_text(coupon: Coupon, locale: str) -> str:
    until = timezone.localtime(coupon.expires_at)
    return f"{day_month(until.date(), locale)}, {until:%H:%M}"


def coupon_line(coupon: Coupon, locale: str) -> str:
    return t(
        locale, "placement_coupon_active", percent=coupon.percent, until=until_text(coupon, locale)
    )


def intro(chat: BotChat, user: User, test_id: int) -> None:
    """Yo'nalish tanlandi: shartlar va «Boshlash» (vaqt shu tugma bilan boshlanadi)."""
    locale = chat.language
    if not allowed(chat, user):
        return
    test = PlacementTest.objects.filter(pk=test_id, is_active=True).first()
    if test is None:
        send(chat.chat_id, t(locale, "placement_closed"))
        return
    running = PlacementAttempt.objects.filter(
        test=test, user=user, finished_at__isnull=True, deadline__gt=timezone.now()
    ).first()
    if running is not None:
        advance(chat, user, running)
        return
    config = rewards.settings()
    values = {"title": escape(test.title), "count": test.questions_count}
    if has_coupon(user):
        text = t(locale, "placement_intro_again", minutes=test.duration_min, **values)
    else:
        text = t(
            locale,
            "placement_intro",
            minutes=test.duration_min,
            good=config.placement_good_percent,
            high=config.placement_high_coupon,
            low=config.placement_low_coupon,
            **values,
        )
    send(chat.chat_id, text, [[button(t(locale, "btn_placement_start"), f"pg:{test.pk}")]])


def start(chat: BotChat, user: User, test_id: int) -> None:
    if not allowed(chat, user):
        return
    test = PlacementTest.objects.filter(pk=test_id).first()
    if test is None:
        send(chat.chat_id, t(chat.language, "placement_closed"))
        return
    try:
        attempt = services.start(test, user)
    except services.PlacementError as exc:
        send(chat.chat_id, escape(str(exc)))
        return
    advance(chat, user, attempt)


def advance(chat: BotChat, user: User, attempt: PlacementAttempt) -> None:
    """Keyingi savol yoki (savol qolmagan / vaqt tugagan bo'lsa) yakun."""
    now = timezone.now()
    step = services.current(attempt) if now < attempt.deadline else None
    if attempt.finished_at is not None or step is None:
        finish(chat, user, attempt)
        return
    index, total, question = step
    layout = Layout.build(question, attempt.seed)
    state: dict[str, Any] = {
        "k": PLACEMENT,
        "a": attempt.pk,
        "q": question.pk,
        "i": index,
        "n": total,
        "sel": [],
    }
    body, hint, rows = render(layout, state, chat.language)
    minutes = max(1, services.seconds_left(attempt, now=now) // 60)
    timer = t(chat.language, "exam_time_left", minutes=minutes)
    message = send(chat.chat_id, f"{body}\n\n{hint}\n{timer}", rows)
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
    attempt: PlacementAttempt,
    layout: Layout,
    response: dict[str, Any],
) -> None:
    locale = chat.language
    state = dict(chat.state.get("quiz") or {})
    try:
        services.answer(attempt, layout.question.pk, response)
    except services.PlacementError as exc:
        forget(chat)
        save_state(chat)
        send(chat.chat_id, escape(str(exc)))
        finish(chat, user, attempt)
        return
    body, _hint, _rows = render(layout, {**state, "sel": []}, locale)
    yours = t(locale, "q_your", answer=short_answer(layout, response))
    edit(chat.chat_id, state.get("m"), f"{body}\n\n{yours}\n{t(locale, 'exam_saved')}")
    forget(chat)
    advance(chat, user, attempt)


def finish(chat: BotChat, user: User, attempt: PlacementAttempt) -> None:
    outcome = services.finish(attempt)
    forget(chat)
    save_state(chat)
    locale = chat.language
    score = outcome.attempt.score or 0
    level = t(locale, f"placement_level_{outcome.level}")
    coupon = outcome.coupon
    if coupon is None or coupon.expires_at is None:
        send(chat.chat_id, t(locale, "placement_done_plain", score=score, level=level))
        return
    text = t(
        locale,
        "placement_done",
        score=score,
        level=level,
        percent=coupon.percent,
        until=until_text(coupon, locale),
    )
    site = link(t(locale, "btn_my_coupon"), links.login_url(user, "/dashboard/rewards", chat))
    send(chat.chat_id, text, [[site]])


def load(chat: BotChat, user: User) -> tuple[PlacementAttempt, Question, Layout] | None:
    state = chat.state.get("quiz") or {}
    attempt_id, question_id = state.get("a"), state.get("q")
    if not isinstance(attempt_id, int) or not isinstance(question_id, int):
        return None
    attempt = PlacementAttempt.objects.filter(
        pk=attempt_id, user=user, finished_at__isnull=True
    ).first()
    question = Question.objects.prefetch_related("choices").filter(pk=question_id).first()
    if attempt is None or question is None:
        return None
    return attempt, question, Layout.build(question, attempt.seed)


def on_button(chat: BotChat, user: User, action: str, args: list[str]) -> str:
    """Daraja testi savoli tugmasi. Qaytadi: qisqa ogohlantirish yoki bo'sh qator."""
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
    if timezone.now() >= attempt.deadline:
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
    """Yozma javob kutilayotgan daraja testi savoli bo'lsa — javob sifatida olinadi."""
    if chat.state.get("await") != "text" or not is_placement(chat):
        return False
    loaded = load(chat, user)
    if loaded is None or loaded[1].kind != Kind.TEXT:
        forget(chat)
        save_state(chat)
        return False
    attempt, _question, layout = loaded
    submit(chat, user, attempt, layout, {"text": text})
    return True


def is_placement(chat: BotChat) -> bool:
    return (chat.state.get("quiz") or {}).get("k") == PLACEMENT
