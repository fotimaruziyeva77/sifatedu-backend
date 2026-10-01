"""Botda takrorlash: o'tilgan dars testlaridan 5 savol, har javobdan keyin ✅ yoki ❌.

Kunlik topshiriqlardan biri. Tugmalar dars testiniki bilan bir xil (qa/qt/qd/qo/qm/qr); holat
`BotChat.state["quiz"]` da `"k": "review"` belgisi bilan. Oxirida natija va (topshiriq
bo'lsa) kunlik topshiriq bajarildi deb belgilanadi.
"""

import random
from typing import Any

from django.utils import timezone

from apps.quizzes import grading
from apps.quizzes.models import Question
from apps.quizzes.services import Layout, load_questions
from apps.rewards import daily
from apps.rewards.models import DailyTask, ReviewAttempt
from apps.users.models import User

from .models import BotChat
from .quiz import (
    Kind,
    forget,
    interpret,
    parse_button,
    redraw,
    render,
    save_state,
    short_answer,
)
from .send import button, edit, send
from .texts import t

REVIEW = "review"


def start(chat: BotChat, user: User) -> None:
    pool = daily.review_pool(user)
    if len(pool) < daily.REVIEW_SIZE:
        send(chat.chat_id, t(chat.language, "review_empty"))
        return
    rng = random.SystemRandom()
    attempt = ReviewAttempt.objects.create(
        user=user,
        question_ids=rng.sample(pool, daily.REVIEW_SIZE),
        seed=rng.randrange(1, 2**31),
    )
    send(chat.chat_id, t(chat.language, "review_intro", count=daily.REVIEW_SIZE))
    advance(chat, user, attempt)


def step(attempt: ReviewAttempt) -> tuple[int, int, Question] | None:
    questions = load_questions(attempt.question_ids)
    ids = [question_id for question_id in attempt.question_ids if question_id in questions]
    for index, question_id in enumerate(ids, 1):
        if str(question_id) not in attempt.answers:
            return index, len(ids), questions[question_id]
    return None


def advance(chat: BotChat, user: User, attempt: ReviewAttempt) -> None:
    found = step(attempt)
    if found is None:
        finish(chat, user, attempt)
        return
    index, total, question = found
    layout = Layout.build(question, attempt.seed)
    state: dict[str, Any] = {
        "k": REVIEW,
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
    chat: BotChat, user: User, attempt: ReviewAttempt, layout: Layout, response: dict[str, Any]
) -> None:
    locale = chat.language
    state = dict(chat.state.get("quiz") or {})
    private = layout.to_private(response)
    if private is None:
        return
    correct = grading.grade(layout.question, layout.choices, private)
    attempt.answers[str(layout.question.pk)] = correct
    attempt.correct += int(correct)
    attempt.save(update_fields=["answers", "correct"])
    body, _hint, _rows = render(layout, {**state, "sel": []}, locale)
    verdict = t(locale, "q_right" if correct else "q_wrong")
    yours = t(locale, "q_your", answer=short_answer(layout, response))
    edit(chat.chat_id, state.get("m"), f"{body}\n\n{yours}\n{verdict}")
    forget(chat)
    advance(chat, user, attempt)


def finish(chat: BotChat, user: User, attempt: ReviewAttempt) -> None:
    forget(chat)
    save_state(chat)
    if attempt.finished_at is None:
        attempt.finished_at = timezone.now()
        attempt.save(update_fields=["finished_at"])
        daily.progress(user.pk, DailyTask.Kind.REVIEW)
    total = len(attempt.question_ids)
    send(
        chat.chat_id,
        t(chat.language, "review_done", correct=attempt.correct, total=total),
        [[button(t(chat.language, "btn_today"), "dt")]],
    )


def load(chat: BotChat, user: User) -> tuple[ReviewAttempt, Layout] | None:
    state = chat.state.get("quiz") or {}
    attempt_id, question_id = state.get("a"), state.get("q")
    if not isinstance(attempt_id, int) or not isinstance(question_id, int):
        return None
    attempt = ReviewAttempt.objects.filter(
        pk=attempt_id, user=user, finished_at__isnull=True
    ).first()
    question = Question.objects.prefetch_related("choices").filter(pk=question_id).first()
    if attempt is None or question is None or str(question.pk) in attempt.answers:
        return None
    return attempt, Layout.build(question, attempt.seed)


def on_button(chat: BotChat, user: User, action: str, args: list[str]) -> str:
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
    attempt, layout = loaded
    count = len(layout.shown)
    if position and not 1 <= position <= count:
        return ""
    selection = [value for value in state.get("sel") or [] if isinstance(value, int)]
    press = interpret(action, layout.question.kind, position, selection, count, locale)
    if press.response is not None:
        submit(chat, user, attempt, layout, press.response)
    elif press.selection is not None:
        redraw(chat, layout, state, press.selection)
    return press.notice


def on_text(chat: BotChat, user: User, text: str) -> bool:
    if chat.state.get("await") != "text" or not is_review(chat):
        return False
    loaded = load(chat, user)
    if loaded is None or loaded[1].question.kind != Kind.TEXT:
        forget(chat)
        save_state(chat)
        return False
    attempt, layout = loaded
    submit(chat, user, attempt, layout, {"text": text})
    return True


def is_review(chat: BotChat) -> bool:
    return (chat.state.get("quiz") or {}).get("k") == REVIEW
