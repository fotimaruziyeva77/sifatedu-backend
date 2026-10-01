"""Test jarayoni: urinish boshlash, javob berish, yakunlash va natijalar."""

import random
import textwrap
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Q
from django.utils import timezone

from apps.catalog.models import Course, Lesson
from apps.core import events
from apps.learning.models import LessonProgress
from apps.notifications.telegram import bot_username
from apps.users.models import User

from . import grading
from .models import Answer, Attempt, Choice, Question, Quiz
from .parser import DraftQuestion

Kind = Question.Kind
# Tugallanmagan urinish shuncha vaqt davom ettiriladi, keyin yangisi boshlanadi.
RESUME_WITHIN = timedelta(hours=24)
THREE_STARS = 90
ONE_STAR = 50
MAX_TEXT = 500


class QuizError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan sabab bilan (API 400)."""


def stars_for(score: int, pass_percent: int) -> int:
    """3 — o'tdi va a'lo (90%+), 2 — o'tdi, 1 — o'tmadi, lekin yarmi to'g'ri, 0 — kam.
    2+ yulduz har doim "o'tdi" degani (o'tish bali 90% dan yuqori bo'lsa ham)."""
    if score >= pass_percent:
        return 3 if score >= THREE_STARS else 2
    return 1 if score >= ONE_STAR else 0


# --- Savollar (javobsiz) ---


def pick(pks: list[int], position: Any) -> int | None:
    """Ekrandagi o'rin (1 dan) → variantning baza ID si; noto'g'ri qiymat — None."""
    if type(position) is not int or not 1 <= position <= len(pks):
        return None
    return pks[position - 1]


@dataclass
class Layout:
    """Savolning shu urinishdagi ko'rinishi.

    Brauzer variantlarni baza ID si bilan emas, ekrandagi o'rni (1 dan) bilan ko'radi: ID lar
    yaratilish tartibida bo'ladi va tartiblashda (ko'pincha tanlashda ham — to'g'ri variant
    birinchi yoziladi) javobni ochib qo'yardi. Aralashtirish urinish bo'yicha barqaror — sahifa
    yangilansa ham tartib o'zgarmaydi. Moslashtirishda chap ustun asl tartibda, o'ng ustun aralash.
    """

    question: Question
    choices: list[Choice]  # asl tartib (moslashtirishda — chap ustun)
    shown: list[Choice]  # ekrandagi tartib (moslashtirishda — o'ng ustun)

    @classmethod
    def build(cls, question: Question, seed: int) -> "Layout":
        choices = list(question.choices.all())
        rng = random.Random(seed * 100_003 + question.pk)  # noqa: S311 - aralashtirish, maxfiylik emas
        shown = list(choices)
        rng.shuffle(shown)
        if question.kind == Kind.ORDER:
            # To'g'ri tartibda chiqib qolmasin (ikki qadamli savolda ham).
            correct = grading.correct_order(choices)
            for _ in range(5):
                if [choice.pk for choice in shown] != correct:
                    break
                rng.shuffle(shown)
            if [choice.pk for choice in shown] == correct and len(shown) > 1:
                shown = [*shown[1:], shown[0]]
        return cls(question, choices, shown)

    def payload(self) -> dict[str, Any]:
        """Brauzerga boradigan savol: to'g'ri javob belgisi va juftlar yo'q."""
        question = self.question
        shown = [{"id": index, "text": choice.text} for index, choice in enumerate(self.shown, 1)]
        payload: dict[str, Any] = {
            "id": question.pk,
            "kind": question.kind,
            "text": question.text,
            "code": question.code,
            "language": question.language,
            "options": shown if question.kind in (Kind.SINGLE, Kind.MULTIPLE) else [],
            "items": shown if question.kind == Kind.ORDER else [],
            "left": [],
            "right": [],
        }
        if question.kind == Kind.MATCH:
            payload["left"] = [
                {"id": index, "text": choice.text} for index, choice in enumerate(self.choices, 1)
            ]
            payload["right"] = [
                {"id": index, "text": choice.match} for index, choice in enumerate(self.shown, 1)
            ]
        return payload

    def to_private(self, response: dict[str, Any]) -> dict[str, Any] | None:
        """Brauzer javobi (o'rinlar) → baza ID lari. Format noto'g'ri bo'lsa — None."""
        kind = self.question.kind
        shown = [choice.pk for choice in self.shown]
        if kind == Kind.SINGLE:
            chosen = pick(shown, response.get("choice"))
            return None if chosen is None else {"choice": chosen}
        if kind in (Kind.MULTIPLE, Kind.ORDER):
            key = "choices" if kind == Kind.MULTIPLE else "order"
            values = response.get(key)
            if not isinstance(values, list):
                return None
            pks = [pick(shown, value) for value in values]
            if None in pks or len(set(pks)) != len(pks):
                return None
            if kind == Kind.ORDER and len(pks) != len(shown):
                return None
            return {key: pks}
        if kind == Kind.TEXT:
            text = response.get("text")
            return {"text": text.strip()[:MAX_TEXT]} if isinstance(text, str) else None
        if kind == Kind.MATCH:
            pairs = response.get("pairs")
            if not isinstance(pairs, dict):
                return None
            left = [choice.pk for choice in self.choices]
            result: dict[str, int] = {}
            for key, value in pairs.items():
                left_pk = pick(left, int(key) if str(key).isdigit() else None)
                right_pk = pick(shown, value)
                if left_pk is None or right_pk is None:
                    return None
                result[str(left_pk)] = right_pk
            return {"pairs": result}
        return None

    def to_public(self, response: dict[str, Any]) -> dict[str, Any]:
        """Baza ID lari → o'rinlar: brauzer javobni ham, to'g'ri javobni ham o'z ID lari bilan
        ko'radi."""
        shown = {choice.pk: index for index, choice in enumerate(self.shown, 1)}
        left = {str(choice.pk): index for index, choice in enumerate(self.choices, 1)}
        result: dict[str, Any] = {}
        for key, value in response.items():
            if key == "choice":
                result[key] = shown.get(value)
            elif key in ("choices", "order"):
                result[key] = [shown[pk] for pk in value if pk in shown]
            elif key == "pairs":
                result[key] = {
                    str(left[left_pk]): shown[right_pk]
                    for left_pk, right_pk in value.items()
                    if left_pk in left and right_pk in shown
                }
            else:
                result[key] = value
        return result


def load_questions(ids: Iterable[int]) -> dict[int, Question]:
    questions = Question.objects.filter(pk__in=list(ids)).prefetch_related("choices")
    return {question.pk: question for question in questions}


def attempt_payload(attempt: Attempt) -> dict[str, Any]:
    questions = load_questions(attempt.question_ids)
    answers = {answer.question_id: answer for answer in attempt.answers.all()}
    items = []
    done = []
    for question_id in attempt.question_ids:
        question = questions.get(question_id)
        if question is None:  # o'qituvchi savolni o'chirgan
            continue
        layout = Layout.build(question, attempt.seed)
        items.append(layout.payload())
        answer = answers.get(question_id)
        if answer is not None:
            done.append(result_payload(layout, answer, reveal=False))
    quiz = attempt.quiz
    return {
        "id": attempt.pk,
        "quiz_id": quiz.pk,
        "title": quiz.title,
        "pass_percent": quiz.pass_percent,
        "total": len(items),
        "questions": items,
        "answers": done,
    }


def result_payload(layout: Layout, answer: Answer | None, *, reveal: bool) -> dict[str, Any]:
    """Javob natijasi. To'g'ri javob va izoh (`reveal`) — faqat test o'tilgach: aks holda
    qayta urinishda javoblarni yodlab olib o'tib ketish mumkin bo'lardi."""
    question = layout.question
    correct_answer = (
        layout.to_public(grading.correct_answer(question, layout.choices)) if reveal else None
    )
    return {
        "question": question.pk,
        "correct": answer.correct if answer else False,
        "response": layout.to_public(answer.response) if answer else {},
        "correct_answer": correct_answer,
        "explanation": question.explanation if reveal else "",
    }


def review(attempt: Attempt) -> list[dict[str, Any]]:
    """O'tilgan test: har savol bo'yicha javob, to'g'ri javob va izoh (javobsizlari ham)."""
    questions = load_questions(attempt.question_ids)
    answers = {answer.question_id: answer for answer in attempt.answers.all()}
    return [
        result_payload(
            Layout.build(questions[question_id], attempt.seed),
            answers.get(question_id),
            reveal=True,
        )
        for question_id in attempt.question_ids
        if question_id in questions
    ]


# --- Urinish ---


def open_attempt(quiz: Quiz, student: Any) -> Attempt | None:
    """Davom ettiriladigan urinish — faqat eng oxirgisi, tugallanmagan va bir kundan yangi bo'lsa.
    "Boshidan boshlash"dan keyin tashlab ketilgan eski urinish qaytib chiqmaydi."""
    latest = (
        Attempt.objects.filter(quiz=quiz, student=student).order_by("-started_at", "-pk").first()
    )
    if latest is None or latest.finished_at is not None:
        return None
    return latest if latest.started_at >= timezone.now() - RESUME_WITHIN else None


def start(quiz: Quiz, student: User, *, fresh: bool = False) -> Attempt:
    """Tugallanmagan urinish bo'lsa — davom ettiriladi (javoblar saqlangan), aks holda yangisi."""
    if not fresh:
        ongoing = open_attempt(quiz, student)
        if ongoing is not None:
            return ongoing
    ids = list(quiz.questions.values_list("pk", flat=True))
    if not ids:
        raise QuizError("Bu testda hali savol yo'q.")
    rng = random.SystemRandom()
    if quiz.questions_per_attempt and quiz.questions_per_attempt < len(ids):
        ids = rng.sample(ids, quiz.questions_per_attempt)
    if quiz.shuffle_questions:
        rng.shuffle(ids)
    return Attempt.objects.create(
        quiz=quiz, student=student, question_ids=ids, seed=rng.randrange(1, 2**31)
    )


def answer(attempt: Attempt, question_id: int, response: dict[str, Any]) -> dict[str, Any]:
    if attempt.finished_at is not None:
        raise QuizError("Bu urinish yakunlangan. Testni qaytadan boshlang.")
    if question_id not in attempt.question_ids:
        raise QuizError("Bu savol ushbu urinishda yo'q.")
    question = Question.objects.prefetch_related("choices").filter(pk=question_id).first()
    if question is None:
        raise QuizError("Savol topilmadi.")
    layout = Layout.build(question, attempt.seed)
    private = layout.to_private(response)
    if private is None:
        raise QuizError("Javob formati noto'g'ri.")
    try:
        with transaction.atomic():
            saved = Answer.objects.create(
                attempt=attempt,
                question=question,
                response=private,
                correct=grading.grade(question, layout.choices, private),
            )
    except IntegrityError as exc:
        raise QuizError("Bu savolga javob berilgan.") from exc
    return result_payload(layout, saved, reveal=False)


def finish(attempt: Attempt) -> dict[str, Any]:
    """Natija: javob berilmagan savollar noto'g'ri hisoblanadi. O'tilsa — dars tugatiladi va
    xatolar ustida ishlash uchun to'g'ri javoblar beriladi."""
    with transaction.atomic():
        locked = Attempt.objects.select_for_update().select_related("quiz").get(pk=attempt.pk)
        # O'qituvchi o'chirgan savol hisobga kirmaydi (unga javob berib bo'lmaydi).
        total = Question.objects.filter(pk__in=locked.question_ids).count()
        if locked.finished_at is None:
            correct = locked.answers.filter(correct=True).count()
            locked.score = round(correct * 100 / total) if total else 0
            locked.stars = stars_for(locked.score, locked.quiz.pass_percent)
            locked.passed = locked.score >= locked.quiz.pass_percent
            locked.finished_at = timezone.now()
            locked.save(update_fields=["score", "stars", "passed", "finished_at"])
            if locked.passed:
                course_id = Lesson.objects.values_list("module__course_id", flat=True).get(
                    pk=locked.quiz.lesson_id
                )
                first = not (
                    Attempt.objects.filter(
                        quiz_id=locked.quiz_id, student_id=locked.student_id, passed=True
                    )
                    .exclude(pk=locked.pk)
                    .exists()
                )
                complete_lesson(locked.student_id, locked.quiz.lesson_id, course_id)
                events.quiz_passed.send(
                    sender=Attempt,
                    user_id=locked.student_id,
                    course_id=course_id,
                    quiz_id=locked.quiz_id,
                    lesson_id=locked.quiz.lesson_id,
                    score=locked.score,
                    first=first,
                )
    correct = locked.answers.filter(correct=True).count()
    best = best_results(locked.student_id, [locked.quiz_id]).get(locked.quiz_id, {})
    return {
        "score": locked.score or 0,
        "stars": locked.stars,
        "passed": locked.passed,
        "correct": correct,
        "total": total,
        "best_score": best.get("score", locked.score or 0),
        "best_stars": best.get("stars", locked.stars),
        "review": review(locked) if locked.passed else [],
    }


def complete_lesson(student_id: int, lesson_id: int, course_id: int) -> None:
    progress, _created = LessonProgress.objects.get_or_create(
        user_id=student_id, lesson_id=lesson_id
    )
    if progress.completed_at is None:
        progress.completed_at = timezone.now()
        progress.save(update_fields=["completed_at", "updated_at"])
        events.lesson_completed.send(
            sender=LessonProgress, user_id=student_id, course_id=course_id, lesson_id=lesson_id
        )


# --- Natijalar ---


def best_results(student_id: int, quiz_ids: Iterable[int]) -> dict[int, dict[str, Any]]:
    """Har test bo'yicha eng yaxshi natija: foiz, yulduz, o'tdimi, urinishlar soni."""
    rows = (
        Attempt.objects.filter(
            student_id=student_id, quiz_id__in=list(quiz_ids), finished_at__isnull=False
        )
        .values("quiz_id")
        .annotate(
            score=Max("score"),
            stars=Max("stars"),
            passed=Count("pk", filter=Q(passed=True)),
            attempts=Count("pk"),
        )
    )
    return {
        row["quiz_id"]: {
            "score": row["score"],
            "stars": row["stars"],
            "passed": row["passed"] > 0,
            "attempts": row["attempts"],
        }
        for row in rows
    }


def quiz_summary(lesson: Lesson, user: Any) -> dict[str, Any] | None:
    """Dars sahifasi uchun: test haqida qisqacha va o'quvchining eng yaxshi natijasi."""
    quiz = Quiz.objects.filter(lesson=lesson).annotate(count=Count("questions")).first()
    if quiz is None or not quiz.count:  # type: ignore[attr-defined]
        return None
    per_attempt = quiz.questions_per_attempt
    count = min(per_attempt, quiz.count) if per_attempt else quiz.count  # type: ignore[attr-defined]
    best: dict[str, Any] = {}
    in_progress = False
    if isinstance(user, User):
        best = best_results(user.pk, [quiz.pk]).get(quiz.pk, {})
        ongoing = open_attempt(quiz, user)
        # Javobsiz ochilgan urinish "davom ettirish" deb ko'rsatilmaydi.
        in_progress = ongoing is not None and ongoing.answers.exists()
    return {
        "id": quiz.pk,
        "title": quiz.title,
        "questions": count,
        "pass_percent": quiz.pass_percent,
        "best_score": best.get("score"),
        "stars": best.get("stars", 0),
        "passed": best.get("passed", False),
        "attempts": best.get("attempts", 0),
        "in_progress": in_progress,
        # Bot sozlangan bo'lsa, test kartasida "Telegram'da ishlash" tugmasi chiqadi.
        "telegram": bool(bot_username()),
    }


def course_stars(user: Any, course: Course) -> dict[int, int]:
    """Kurs dasturi uchun: testli darslar → eng yaxshi yulduz (test ishlanmagan bo'lsa 0)."""
    quizzes = dict(
        Quiz.objects.filter(lesson__module__course=course)
        .annotate(count=Count("questions"))
        .filter(count__gt=0)
        .values_list("pk", "lesson_id")
    )
    if not quizzes:
        return {}
    best = best_results(user.pk, quizzes) if isinstance(user, User) else {}
    return {
        lesson_id: best.get(quiz_id, {}).get("stars", 0) for quiz_id, lesson_id in quizzes.items()
    }


# --- O'qituvchi ---


@transaction.atomic
def import_questions(quiz: Quiz, drafts: list[DraftQuestion]) -> int:
    """ "Tez kiritish": savollar mavjudlarining oxiriga qo'shiladi."""
    start_at = (quiz.questions.aggregate(last=Max("order"))["last"] or 0) + 1
    for offset, draft in enumerate(drafts):
        question = Question.objects.create(
            quiz=quiz,
            kind=draft.kind,
            text=draft.text,
            code=textwrap.dedent("\n".join(draft.code)).strip("\n"),
            language=draft.language,
            explanation="\n".join(draft.explanation),
            order=start_at + offset,
        )
        Choice.objects.bulk_create(
            Choice(
                question=question,
                text=choice.text[:500],
                is_correct=choice.is_correct,
                match=choice.match[:500],
                order=index + 1,
            )
            for index, choice in enumerate(draft.choices)
        )
    return len(drafts)


def question_stats(quiz: Quiz) -> list[dict[str, Any]]:
    """Har savol bo'yicha: nechta javob va to'g'ri javoblar foizi (qiyin savollar ko'rinadi)."""
    rows = quiz.questions.annotate(
        answered=Count("answers"), right=Count("answers", filter=Q(answers__correct=True))
    ).order_by("order", "pk")
    return [
        {
            "question": question,
            "answered": question.answered,  # type: ignore[attr-defined]
            "percent": (
                round(question.right * 100 / question.answered)  # type: ignore[attr-defined]
                if question.answered  # type: ignore[attr-defined]
                else None
            ),
        }
        for question in rows
    ]


def group_quiz_stats(user_ids: list[int], course_id: int) -> dict[int, dict[str, Any]]:
    """Guruh sahifasi: har o'quvchining o'rtacha eng yaxshi natijasi va o'tgan testlari."""
    rows = (
        Attempt.objects.filter(
            student_id__in=user_ids,
            quiz__lesson__module__course_id=course_id,
            finished_at__isnull=False,
        )
        .values("student_id", "quiz_id")
        .annotate(best=Max("score"), passed=Count("pk", filter=Q(passed=True)))
    )
    stats: dict[int, dict[str, Any]] = {}
    for row in rows:
        item = stats.setdefault(row["student_id"], {"scores": [], "passed": 0})
        item["scores"].append(row["best"] or 0)
        item["passed"] += 1 if row["passed"] else 0
    return {
        student: {
            "quiz_average": round(sum(item["scores"]) / len(item["scores"])),
            "quiz_passed": item["passed"],
        }
        for student, item in stats.items()
    }
