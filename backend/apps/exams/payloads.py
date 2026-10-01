"""API javoblari: o'quvchi va o'qituvchi uchun imtihon ko'rinishi."""

from datetime import datetime
from typing import Any

from django.conf import settings
from django.utils import timezone, translation

from apps.quizzes.services import Layout, load_questions
from apps.users.models import User
from apps.videos import s3

from . import services
from .models import Exam, ExamAttempt, ExamResult, ExamTask, TaskAnswer, TaskAnswerFile

LINK_TTL = settings.HLS_SIGNED_URL_TTL_SEC


def file_payload(item: TaskAnswerFile) -> dict[str, Any]:
    url = s3.sign_get(item.file.name, LINK_TTL, download_name=None if item.is_image else item.name)
    return {
        "id": item.pk,
        "name": item.name,
        "size": item.size,
        "is_image": item.is_image,
        "url": url,
    }


def answer_payload(answer: TaskAnswer | None) -> dict[str, Any] | None:
    if answer is None:
        return None
    reviewer = answer.reviewer
    return {
        "id": answer.pk,
        "text": answer.text,
        "code": answer.code,
        "language": answer.language,
        "link": answer.link,
        "files": [file_payload(item) for item in answer.files.all()],
        "updated_at": answer.updated_at,
        "score": answer.score,
        "feedback": answer.feedback,
        "reviewer_name": (reviewer.get_full_name() or reviewer.phone) if reviewer else "",
        "reviewed_at": answer.reviewed_at,
    }


def state(exam: Exam, user: Any, now: datetime) -> str:
    if now < exam.opens_at:
        return "UPCOMING"
    return "OPEN" if now < services.window_end(exam, user) else "CLOSED"


def test_payload(exam: Exam, user: Any, attempt: ExamAttempt | None, now: datetime) -> dict:
    finished = attempt is not None and attempt.finished_at is not None
    reveal = finished and services.revealed(exam, user, now=now)
    questions: list[dict[str, Any]] = []
    if reveal and attempt is not None:
        loaded = load_questions(attempt.question_ids)
        questions = [
            Layout.build(loaded[question_id], attempt.seed).payload()
            for question_id in attempt.question_ids
            if question_id in loaded
        ]
    return {
        "questions": len(attempt.question_ids) if attempt else exam.questions_count,
        "minutes": exam.duration_min,
        "started": attempt is not None,
        "finished": finished,
        "deadline": attempt.deadline if attempt else None,
        "seconds_left": services.seconds_left(attempt, now=now) if attempt else 0,
        "score": attempt.score if finished and attempt else None,
        "review": services.review(attempt) if reveal and attempt else [],
        "review_questions": questions,
    }


def outcome(result: ExamResult | None) -> dict[str, Any] | None:
    if result is None:
        return None
    return {
        "test_score": result.test_score,
        "practical_score": result.practical_score,
        "total": result.total,
        "passed": result.passed,
        "final": result.final_at is not None,
    }


def card(exam: Exam, user: User, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or timezone.now()
    attempt = ExamAttempt.objects.filter(exam=exam, student=user).first()
    tasks = exam.tasks.count()
    submitted = TaskAnswer.objects.filter(task__exam=exam, student=user).count()
    with translation.override(user.locale or "uz"):
        course_title = str(exam.course.title)
    return {
        "id": exam.pk,
        "course_title": course_title,
        "course_slug": exam.course.slug,
        "opens_at": exam.opens_at,
        "closes_at": services.window_end(exam, user),
        "state": state(exam, user, now),
        "can_take": services.available(exam, user, now=now),
        "pass_percent": exam.pass_percent,
        "test_weight": exam.test_weight,
        "tasks_total": tasks,
        "tasks_submitted": submitted,
        "test": test_payload(exam, user, attempt, now),
        "result": outcome(ExamResult.objects.filter(exam=exam, student=user).first()),
    }


def detail(exam: Exam, user: User, *, now: datetime | None = None) -> dict[str, Any]:
    payload = card(exam, user, now=now)
    answers = {
        answer.task_id: answer
        for answer in TaskAnswer.objects.filter(task__exam=exam, student=user)
        .select_related("reviewer")
        .prefetch_related("files")
    }
    payload["tasks"] = [task_payload(task, answers.get(task.pk)) for task in exam.tasks.all()]
    return payload


def task_payload(task: ExamTask, answer: TaskAnswer | None = None) -> dict[str, Any]:
    return {
        "id": task.pk,
        "order": task.order,
        "title": task.title,
        "instructions": task.instructions,
        "answer": answer_payload(answer),
    }


# --- O'qituvchi ---


def teacher_card(exam: Exam, viewer: User) -> dict[str, Any]:
    students = [person.pk for person in services.students_of(viewer, exam)]
    return {
        "id": exam.pk,
        "course_title": str(exam.course.title),
        "month": exam.month,
        "status": exam.status,
        "opens_at": exam.opens_at,
        "closes_at": exam.closes_at,
        "students": len(students),
        "tested": ExamAttempt.objects.filter(
            exam=exam, student_id__in=students, finished_at__isnull=False
        ).count(),
        "to_grade": TaskAnswer.objects.filter(
            task__exam=exam, student_id__in=students, score__isnull=True
        ).count(),
    }


def teacher_detail(exam: Exam, viewer: User) -> dict[str, Any]:
    people = services.students_of(viewer, exam)
    ids = [person.pk for person in people]
    tasks = list(exam.tasks.all())
    attempts = {row.student_id: row for row in ExamAttempt.objects.filter(exam=exam)}
    results = {row.student_id: row for row in ExamResult.objects.filter(exam=exam)}
    extensions = {row.student_id: row.until for row in exam.extensions.all()}
    answers: dict[tuple[int, int], TaskAnswer] = {
        (answer.student_id, answer.task_id): answer
        for answer in TaskAnswer.objects.filter(task__exam=exam, student_id__in=ids)
        .select_related("reviewer")
        .prefetch_related("files")
    }
    groups = services.groups_of(ids, exam.course_id)
    rows = []
    for person in people:
        attempt = attempts.get(person.pk)
        result = results.get(person.pk)
        rows.append(
            {
                "student_id": person.pk,
                "name": person.get_full_name() or person.phone,
                "group": groups.get(person.pk, ""),
                "test_score": attempt.score if attempt else None,
                "test_started": attempt is not None,
                "tasks": [
                    {
                        "task_id": task.pk,
                        "answer": answer_payload(answers.get((person.pk, task.pk))),
                    }
                    for task in tasks
                ],
                "total": result.total if result else None,
                "passed": result.passed if result else None,
                "final": bool(result and result.final_at),
                "extension_until": extensions.get(person.pk),
            }
        )
    return {
        **teacher_card(exam, viewer),
        "pass_percent": exam.pass_percent,
        "test_weight": exam.test_weight,
        "tasks": [task_payload(task) for task in tasks],
        "rows": rows,
    }
