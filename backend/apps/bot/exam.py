"""Oylik imtihon testi botda: dars testidagi tugmalar, lekin javobdan keyin natija aytilmaydi.

Urinish bitta — saytda boshlangan bo'lsa, botda davom etadi (va aksincha). Vaqt serverda: har
savol oldidan tekshiriladi, tugagan bo'lsa test yakunlanadi. Holat — `BotChat.state["quiz"]`
(`"k": "exam"` belgisi bilan): tugmalar dars testiniki bilan bir xil (qa/qt/qd/qo/qm/qr).
"""

from typing import Any

from django.utils import timezone, translation

from apps.exams import services as exams
from apps.exams.models import Exam, ExamAttempt
from apps.quizzes.models import Question
from apps.quizzes.services import Layout
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
    save_state,
    short_answer,
)
from .send import button, edit, escape, link, send
from .texts import t

EXAM = "exam"


def course_title(exam: Exam, locale: str) -> str:
    with translation.override(locale):
        return str(exam.course.title)


def open_exams(user: User) -> list[Exam]:
    """Botda ishlash mumkin bo'lgan imtihonlar: ochiq va test qismi hali topshirilmagan."""
    now = timezone.now()
    finished = set(
        ExamAttempt.objects.filter(student=user, finished_at__isnull=False).values_list(
            "exam_id", flat=True
        )
    )
    return [
        exam
        for exam in exams.exams_for(user, now=now)
        if exam.pk not in finished and exams.available(exam, user, now=now)
    ]


def site_link(chat: BotChat, user: User, exam: Exam) -> dict[str, Any]:
    return link(
        t(chat.language, "btn_exam_tasks"),
        links.login_url(user, f"/dashboard/exams/{exam.pk}", chat),
    )


def intro(chat: BotChat, user: User, exam_id: int) -> None:
    """ "🏆 Oylik imtihon" bosildi: shartlar va "Boshlash" (vaqt shu tugma bilan boshlanadi)."""
    locale = chat.language
    exam = Exam.objects.select_related("course").filter(pk=exam_id).first()
    if exam is None or not exams.available(exam, user):
        send(chat.chat_id, t(locale, "exam_closed"))
        return
    attempt = ExamAttempt.objects.filter(exam=exam, student=user).first()
    if attempt is not None and attempt.finished_at is None:
        start(chat, user, exam.pk)
        return
    if attempt is not None:
        send(chat.chat_id, t(locale, "exam_already", score=attempt.score or 0))
        return
    text = t(
        locale,
        "exam_intro",
        course=escape(course_title(exam, locale)),
        count=exam.questions_count,
        minutes=exam.duration_min,
    )
    rows = [[button(t(locale, "btn_exam_start"), f"xg:{exam.pk}")], [site_link(chat, user, exam)]]
    send(chat.chat_id, text, rows)


def start(chat: BotChat, user: User, exam_id: int) -> None:
    exam = Exam.objects.select_related("course").filter(pk=exam_id).first()
    if exam is None:
        send(chat.chat_id, t(chat.language, "exam_closed"))
        return
    try:
        attempt = exams.start_test(exam, user)
    except exams.ExamError as exc:
        send(chat.chat_id, escape(str(exc)))
        return
    advance(chat, user, attempt)


def advance(chat: BotChat, user: User, attempt: ExamAttempt) -> None:
    """Keyingi savol yoki (savol qolmagan / vaqt tugagan bo'lsa) yakun."""
    now = timezone.now()
    step = exams.current(attempt) if now < attempt.deadline else None
    if attempt.finished_at is not None or step is None:
        finish(chat, user, attempt)
        return
    index, total, question = step
    layout = Layout.build(question, attempt.seed)
    state: dict[str, Any] = {
        "k": EXAM,
        "a": attempt.pk,
        "q": question.pk,
        "i": index,
        "n": total,
        "sel": [],
    }
    body, hint, rows = render(layout, state, chat.language)
    minutes = max(1, exams.seconds_left(attempt, now=now) // 60)
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
    chat: BotChat, user: User, attempt: ExamAttempt, layout: Layout, response: dict[str, Any]
) -> None:
    locale = chat.language
    state = dict(chat.state.get("quiz") or {})
    try:
        exams.answer_test(attempt, layout.question.pk, response)
    except exams.ExamError as exc:
        forget(chat)
        save_state(chat)
        send(chat.chat_id, escape(str(exc)))
        attempt.refresh_from_db()
        if attempt.finished_at is not None:
            finish(chat, user, attempt)
        return
    body, _hint, _rows = render(layout, {**state, "sel": []}, locale)
    yours = t(locale, "q_your", answer=short_answer(layout, response))
    edit(chat.chat_id, state.get("m"), f"{body}\n\n{yours}\n{t(locale, 'exam_saved')}")
    forget(chat)
    advance(chat, user, attempt)


def finish(chat: BotChat, user: User, attempt: ExamAttempt) -> None:
    attempt = exams.finish_test(attempt)
    forget(chat)
    save_state(chat)
    exam = Exam.objects.select_related("course").get(pk=attempt.exam_id)
    send(
        chat.chat_id,
        t(chat.language, "exam_done", score=attempt.score or 0),
        [[site_link(chat, user, exam)]],
    )


def load(chat: BotChat, user: User) -> tuple[ExamAttempt, Question, Layout] | None:
    state = chat.state.get("quiz") or {}
    attempt_id, question_id = state.get("a"), state.get("q")
    if not isinstance(attempt_id, int) or not isinstance(question_id, int):
        return None
    attempt = ExamAttempt.objects.filter(
        pk=attempt_id, student=user, finished_at__isnull=True
    ).first()
    question = Question.objects.prefetch_related("choices").filter(pk=question_id).first()
    if attempt is None or question is None:
        return None
    return attempt, question, Layout.build(question, attempt.seed)


def on_button(chat: BotChat, user: User, action: str, args: list[str]) -> str:
    """Imtihon savoli tugmasi. Qaytadi: qisqa ogohlantirish yoki bo'sh qator."""
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
    """Yozma javob kutilayotgan imtihon savoli bo'lsa — javob sifatida olinadi."""
    if chat.state.get("await") != "text" or (chat.state.get("quiz") or {}).get("k") != EXAM:
        return False
    loaded = load(chat, user)
    if loaded is None or loaded[1].kind != Kind.TEXT:
        forget(chat)
        save_state(chat)
        return False
    attempt, _question, layout = loaded
    submit(chat, user, attempt, layout, {"text": text})
    return True


def is_exam(chat: BotChat) -> bool:
    return (chat.state.get("quiz") or {}).get("k") == EXAM
