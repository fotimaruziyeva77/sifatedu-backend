"""Dars testi botda: savollar tugmalar bilan, har javobdan keyin faqat ✅ yoki ❌.

Savollar, aralashtirish va baholash saytdagi bilan bitta (`apps.quizzes.services`): bot ham
brauzer kabi variantlarni ekrandagi o'rni (1 dan) bilan yuboradi. To'g'ri javoblar va izohlar
test o'tilgach ko'rsatiladi.

Holat — `BotChat.state["quiz"]`: {"a": urinish, "q": savol, "i": tartib raqami, "n": jami,
"sel": tanlanganlar, "m": savol xabari}. Tugmada urinish va savol bor: eski xabardagi tugma
bosilsa, "savol yopilgan" deyiladi.
"""

from dataclasses import dataclass
from typing import Any

from django.db.models import Count

from apps.catalog.models import Course, Lesson
from apps.learning import access
from apps.live.gates import closed_lessons, lesson_order, tasks_open
from apps.quizzes import services
from apps.quizzes.models import Attempt, Question, Quiz
from apps.users.models import User

from . import links
from .models import BotChat
from .send import Rows, button, edit, escape, link, rows_of, send, split
from .texts import t

Kind = Question.Kind
Layout = services.Layout
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def letter(position: int) -> str:
    return LETTERS[position - 1] if 1 <= position <= len(LETTERS) else str(position)


def lesson_path(course: Course, lesson: Lesson) -> str:
    return f"/dashboard/courses/{course.slug}/lessons/{lesson.pk}"


def next_lesson(lesson: Lesson) -> Lesson | None:
    order = lesson_order(lesson.module.course_id)
    index = order.index(lesson.pk) if lesson.pk in order else len(order)
    return Lesson.objects.filter(pk=order[index + 1]).first() if index + 1 < len(order) else None


def closed_reason(user: User, lesson: Lesson, locale: str) -> str | None:
    """Test nega ochilmaydi (o'quvchiga tushunarli matn). Ochiq bo'lsa — None."""
    lock = access.lesson_lock(user, lesson)
    if lock is not None:
        reason, blocker_id = lock
        blocker = Lesson.objects.filter(pk=blocker_id).first() if blocker_id else None
        if reason == access.LOCK_QUIZ and blocker is not None:
            return t(locale, "quiz_locked", lesson=escape(blocker.title))
        return t(locale, "quiz_no_access")
    if not tasks_open(user, lesson):
        return t(locale, "quiz_offline_locked")
    return None


# --- Savolni ko'rsatish ---


def render(layout: Layout, state: dict[str, Any], locale: str) -> tuple[str, str, Rows]:
    """Savol matni (variantlar bilan), yo'riqnoma va tugmalar."""
    question = layout.question
    ref = f"{state['a']}:{state['q']}"
    selection = [value for value in state.get("sel") or [] if isinstance(value, int)]
    shown = layout.shown
    count = len(shown)
    lines = [t(locale, "q_head", index=state["i"], total=state["n"], text=escape(question.text))]
    if question.code:
        language = f' class="language-{escape(question.language)}"' if question.language else ""
        lines.append(f"<pre><code{language}>{escape(question.code)}</code></pre>")
    rows: Rows = []
    kind = question.kind
    if kind in (Kind.SINGLE, Kind.MULTIPLE):
        lines.append(
            "\n".join(
                f"{letter(index)}) {escape(item.text)}" for index, item in enumerate(shown, 1)
            )
        )
        if kind == Kind.SINGLE:
            hint = t(locale, "q_single_hint")
            rows = rows_of(
                [button(letter(index), f"qa:{ref}:{index}") for index in range(1, count + 1)], 4
            )
        else:
            hint = t(locale, "q_multiple_hint")
            marks = [
                button(("✅ " if index in selection else "") + letter(index), f"qt:{ref}:{index}")
                for index in range(1, count + 1)
            ]
            rows = [*rows_of(marks, 4), [button(t(locale, "btn_done"), f"qd:{ref}")]]
    elif kind == Kind.ORDER:
        lines.append(
            "\n".join(f"{index}) {escape(item.text)}" for index, item in enumerate(shown, 1))
        )
        hint = t(locale, "q_order_hint")
        if selection:
            chosen = " → ".join(str(index) for index in selection)
            hint += "\n" + t(locale, "q_order_chosen", items=chosen)
        rest = [index for index in range(1, count + 1) if index not in selection]
        rows = rows_of([button(str(index), f"qo:{ref}:{index}") for index in rest], 5)
    elif kind == Kind.MATCH:
        left = layout.choices
        lines.append(
            "\n".join(f"{index}) {escape(item.text)}" for index, item in enumerate(left, 1))
        )
        lines.append(
            "\n".join(
                f"{letter(index)}) {escape(item.match)}" for index, item in enumerate(shown, 1)
            )
        )
        hint = t(locale, "q_match_hint")
        if selection:
            pairs = ", ".join(
                f"{index} → {letter(value)}" for index, value in enumerate(selection, 1)
            )
            hint += "\n" + pairs
        if len(selection) < len(left):
            hint += "\n" + t(locale, "q_match_prompt", item=escape(left[len(selection)].text))
        rest = [index for index in range(1, count + 1) if index not in selection]
        rows = rows_of([button(letter(index), f"qm:{ref}:{index}") for index in rest], 5)
    else:
        hint = t(locale, "q_text_hint")
    if selection and kind in (Kind.ORDER, Kind.MATCH):
        rows.append([button(t(locale, "btn_reset"), f"qr:{ref}")])
    return "\n\n".join(lines), hint, rows


def short_answer(layout: Layout, response: dict[str, Any]) -> str:
    """Savol ostida: "Javobingiz: B" — variantlar xabarning o'zida harf bilan turibdi."""
    kind = layout.question.kind
    if kind == Kind.SINGLE:
        return letter(int(response.get("choice") or 0))
    if kind == Kind.MULTIPLE:
        return ", ".join(letter(value) for value in response.get("choices", []))
    if kind == Kind.ORDER:
        return " → ".join(str(value) for value in response.get("order", []))
    if kind == Kind.MATCH:
        pairs = response.get("pairs") or {}
        return ", ".join(f"{key} → {letter(pairs[key])}" for key in sorted(pairs, key=int))
    return escape(response.get("text", ""))


def full_answer(layout: Layout, response: dict[str, Any] | None, locale: str) -> str:
    """Xatolar ustida ishlashda: javob variantlarning o'z matni bilan."""
    kind = layout.question.kind
    shown = layout.shown

    def at(position: Any) -> Any:
        if isinstance(position, int) and 1 <= position <= len(shown):
            return shown[position - 1]
        return None

    response = response or {}
    parts: list[str] = []
    if kind in (Kind.SINGLE, Kind.MULTIPLE):
        positions = response.get("choices") or (
            [response["choice"]] if "choice" in response else []
        )
        parts = [item.text for item in map(at, positions) if item is not None]
        value = ", ".join(parts)
    elif kind == Kind.ORDER:
        parts = [item.text for item in map(at, response.get("order", [])) if item is not None]
        value = " → ".join(parts)
    elif kind == Kind.MATCH:
        pairs = response.get("pairs") or {}
        left = layout.choices
        for key in sorted(pairs, key=int):
            right = at(pairs[key])
            if right is not None and 1 <= int(key) <= len(left):
                parts.append(f"{left[int(key) - 1].text} — {right.match}")
        value = "; ".join(parts)
    else:
        value = str(response.get("text") or "")
    return escape(value) if value else t(locale, "no_answer")


# --- Test jarayoni ---


def current(attempt: Attempt) -> tuple[int, int, Question] | None:
    """Joriy savol: birinchi javobsiz savol (tartib raqami, jami, savol). Hammasi javoblangan
    bo'lsa — None. O'qituvchi o'chirgan savol hisobga kirmaydi."""
    questions = services.load_questions(attempt.question_ids)
    ids = [question_id for question_id in attempt.question_ids if question_id in questions]
    answered = set(attempt.answers.values_list("question_id", flat=True))
    for index, question_id in enumerate(ids, 1):
        if question_id not in answered:
            return index, len(ids), questions[question_id]
    return None


def save_state(chat: BotChat) -> None:
    chat.save(update_fields=["state", "updated_at"])


def forget(chat: BotChat) -> None:
    chat.state.pop("quiz", None)
    chat.state.pop("await", None)


def start(chat: BotChat, user: User, quiz_id: int, *, fresh: bool = False) -> None:
    """Testni boshlaydi yoki tugallanmaganini davom ettiradi (`fresh` — yangisini)."""
    locale = chat.language
    quiz = Quiz.objects.select_related("lesson__module__course").filter(pk=quiz_id).first()
    if quiz is None or not quiz.questions.exists():
        send(chat.chat_id, t(locale, "quiz_missing"))
        return
    reason = closed_reason(user, quiz.lesson, locale)
    if reason is not None:
        send(chat.chat_id, reason)
        return
    ongoing = None if fresh else services.open_attempt(quiz, user)
    if ongoing is not None and ongoing.answers.exists():
        attempt = ongoing
        send(chat.chat_id, t(locale, "quiz_resume", title=escape(quiz.title)))
    else:
        attempt = ongoing or services.start(quiz, user, fresh=True)
        send(
            chat.chat_id,
            t(
                locale,
                "quiz_intro",
                title=escape(quiz.title),
                lesson=escape(quiz.lesson.title),
                count=len(attempt.question_ids),
                percent=quiz.pass_percent,
            ),
        )
    advance(chat, user, attempt)


def advance(chat: BotChat, user: User, attempt: Attempt) -> None:
    """Keyingi savolni yuboradi yoki (savol qolmagan bo'lsa) natijani."""
    step = current(attempt)
    if step is None:
        finish(chat, user, attempt)
        return
    index, total, question = step
    layout = Layout.build(question, attempt.seed)
    state: dict[str, Any] = {"a": attempt.pk, "q": question.pk, "i": index, "n": total, "sel": []}
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
    chat: BotChat, user: User, attempt: Attempt, layout: Layout, response: dict[str, Any]
) -> None:
    locale = chat.language
    state = dict(chat.state.get("quiz") or {})
    try:
        result = services.answer(attempt, layout.question.pk, response)
    except services.QuizError as exc:
        send(chat.chat_id, escape(str(exc)))
        return
    body, _hint, _rows = render(layout, {**state, "sel": []}, locale)
    verdict = t(locale, "q_right" if result["correct"] else "q_wrong")
    yours = t(locale, "q_your", answer=short_answer(layout, response))
    edit(chat.chat_id, state.get("m"), f"{body}\n\n{yours}\n{verdict}")
    forget(chat)
    advance(chat, user, attempt)


def finish(chat: BotChat, user: User, attempt: Attempt) -> None:
    locale = chat.language
    result = services.finish(attempt)
    quiz = Quiz.objects.select_related("lesson__module__course").get(pk=attempt.quiz_id)
    lesson = quiz.lesson
    course = lesson.module.course
    forget(chat)
    save_state(chat)
    numbers = {"score": result["score"], "correct": result["correct"], "total": result["total"]}
    if not result["passed"]:
        text = t(locale, "result_fail", percent=quiz.pass_percent, **numbers)
        rows: Rows = [
            [button(t(locale, "btn_retry"), f"qn:{quiz.pk}")],
            [
                link(
                    t(locale, "btn_video"),
                    links.login_url(user, lesson_path(course, lesson), chat),
                )
            ],
        ]
        send(chat.chat_id, text, rows)
        return
    blocks = [t(locale, "result_pass", stars="⭐" * result["stars"], **numbers)]
    blocks += review_blocks(attempt, result["review"], locale)
    following = next_lesson(lesson)
    if following is not None:
        target = link(
            t(locale, "btn_next_lesson"),
            links.login_url(user, lesson_path(course, following), chat),
        )
    else:
        target = link(
            t(locale, "btn_course"),
            links.login_url(user, f"/dashboard/courses/{course.slug}", chat),
        )
    messages = split(blocks)
    for text in messages[:-1]:
        send(chat.chat_id, text)
    send(chat.chat_id, messages[-1], [[target]])


def review_blocks(attempt: Attempt, review: list[dict[str, Any]], locale: str) -> list[str]:
    """Xatolar: savol, o'quvchi javobi, to'g'ri javob va izoh."""
    mistakes = [item for item in review if not item["correct"]]
    if not mistakes:
        return [t(locale, "review_all_right")]
    questions = services.load_questions(attempt.question_ids)
    numbers = {
        question_id: index
        for index, question_id in enumerate(
            [question_id for question_id in attempt.question_ids if question_id in questions], 1
        )
    }
    blocks = [t(locale, "review_title")]
    for item in mistakes:
        question = questions.get(item["question"])
        if question is None:
            continue
        layout = Layout.build(question, attempt.seed)
        block = t(
            locale,
            "review_item",
            index=numbers[question.pk],
            question=escape(question.text),
            yours=full_answer(layout, item["response"], locale),
            right=full_answer(layout, item["correct_answer"], locale),
        )
        if question.explanation:
            block += "\n" + t(locale, "review_note", text=escape(question.explanation))
        blocks.append(block)
    return blocks


@dataclass(frozen=True)
class Press:
    """Tugma bosilishining natijasi: tayyor javob, yangilangan tanlov yoki ogohlantirish."""

    response: dict[str, Any] | None = None
    selection: list[int] | None = None
    notice: str = ""


def interpret(
    action: str, kind: str, position: int, selection: list[int], count: int, locale: str
) -> Press:
    """Savol tugmasi (qa/qt/qd/qo/qm/qr): nima qilish kerak. Dars testi va imtihon uchun bitta."""
    if action == "qa" and kind == Kind.SINGLE and position:
        return Press(response={"choice": position})
    if action == "qt" and kind == Kind.MULTIPLE and position:
        toggled = [value for value in selection if value != position]
        if position not in selection:
            toggled.append(position)
        return Press(selection=toggled)
    if action == "qd" and kind == Kind.MULTIPLE:
        if not selection:
            return Press(notice=t(locale, "q_pick_one"))
        return Press(response={"choices": sorted(selection)})
    if action in ("qo", "qm") and kind in (Kind.ORDER, Kind.MATCH) and position:
        chosen = selection if position in selection else [*selection, position]
        if len(chosen) < count:
            return Press(selection=chosen)
        if kind == Kind.ORDER:
            return Press(response={"order": chosen})
        return Press(
            response={"pairs": {str(index): value for index, value in enumerate(chosen, 1)}}
        )
    if action == "qr":
        return Press(selection=[])
    return Press()


def parse_button(args: list[str]) -> tuple[int, int, int] | None:
    """Tugma ma'lumoti: urinish, savol va (bo'lsa) variant o'rni."""
    try:
        return int(args[0]), int(args[1]), int(args[2]) if len(args) > 2 else 0
    except (IndexError, ValueError):
        return None


def redraw(chat: BotChat, layout: Layout, state: dict[str, Any], selection: list[int]) -> None:
    state["sel"] = selection
    chat.state["quiz"] = state
    save_state(chat)
    body, hint, rows = render(layout, state, chat.language)
    edit(chat.chat_id, state.get("m"), f"{body}\n\n{hint}", rows)


def on_button(chat: BotChat, user: User, action: str, args: list[str]) -> str:
    """Test tugmasi (qa/qt/qd/qo/qm/qr). Qaytadi: qisqa ogohlantirish yoki bo'sh qator."""
    locale = chat.language
    parsed = parse_button(args)
    if parsed is None:
        return ""
    attempt_id, question_id, position = parsed
    state = dict(chat.state.get("quiz") or {})
    if state.get("a") != attempt_id or state.get("q") != question_id:
        return t(locale, "q_stale")
    attempt = (
        Attempt.objects.select_related("quiz")
        .filter(pk=attempt_id, student=user, finished_at__isnull=True)
        .first()
    )
    question = Question.objects.prefetch_related("choices").filter(pk=question_id).first()
    if attempt is None or question is None:
        forget(chat)
        save_state(chat)
        return t(locale, "q_stale")
    layout = Layout.build(question, attempt.seed)
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
    """Yozma javob kutilayotgan bo'lsa, xabar javob sifatida olinadi. Qaytadi: olindimi."""
    state = chat.state.get("quiz") or {}
    attempt_id, question_id = state.get("a"), state.get("q")
    if chat.state.get("await") != "text" or not isinstance(attempt_id, int) or state.get("k"):
        return False
    attempt = (
        Attempt.objects.select_related("quiz")
        .filter(pk=attempt_id, student=user, finished_at__isnull=True)
        .first()
    )
    question = (
        Question.objects.prefetch_related("choices").filter(pk=question_id).first()
        if isinstance(question_id, int)
        else None
    )
    if attempt is None or question is None or question.kind != Kind.TEXT:
        forget(chat)
        save_state(chat)
        return False
    submit(chat, user, attempt, Layout.build(question, attempt.seed), {"text": text})
    return True


# --- "Testlar" ro'yxati ---


@dataclass(frozen=True)
class Available:
    quiz: Quiz
    course_title: str
    in_progress: bool


def available(user: User) -> tuple[list[Available], int]:
    """Ishlash mumkin bo'lgan (hali o'tilmagan va ochiq) testlar va o'tilganlar soni."""
    quizzes = list(
        Quiz.objects.filter(lesson__module__course__in=access.enrolled_courses(user))
        .annotate(count=Count("questions"))
        .filter(count__gt=0)
        .select_related("lesson__module__course")
        .order_by(
            "lesson__module__course__order",
            "lesson__module__course_id",
            "lesson__module__order",
            "lesson__module_id",
            "lesson__order",
            "lesson_id",
        )
    )
    passed = set(
        Attempt.objects.filter(student=user, passed=True, quiz__in=quizzes).values_list(
            "quiz_id", flat=True
        )
    )
    shut: dict[int, set[int]] = {}
    found = []
    for quiz in quizzes:
        if quiz.pk in passed:
            continue
        course = quiz.lesson.module.course
        if course.pk not in shut:
            shut[course.pk] = set(access.quiz_gate(user, course.pk)) | closed_lessons(
                user, course.pk
            )
        if quiz.lesson_id in shut[course.pk]:
            continue
        ongoing = services.open_attempt(quiz, user)
        found.append(Available(quiz, str(course.title), ongoing is not None))
    return found, len(passed)
