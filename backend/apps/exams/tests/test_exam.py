"""Oylik imtihon: test (bitta urinish, vaqt, natijasiz javob), amaliy qism, baholash, natija."""

from datetime import date, timedelta
from typing import Any
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.exams import services
from apps.exams.models import Exam, ExamAttempt, ExamResult, TaskAnswer
from apps.notifications.models import Notification
from apps.quizzes import grading
from apps.quizzes.models import Question
from apps.quizzes.services import Layout

from .conftest import World, api, make_user

pytestmark = pytest.mark.django_db


def right(layout: Layout) -> dict[str, Any]:
    """To'g'ri javob — ekrandagi o'rinlar bilan (brauzer yuboradigan ko'rinishda)."""
    public = layout.to_public(grading.correct_answer(layout.question, layout.choices))
    kind = layout.question.kind
    if kind == Question.Kind.SINGLE:
        return {"choice": public["choices"][0]}
    if kind == Question.Kind.TEXT:
        return {"text": public["text"]}
    return public


def answer_all(attempt: ExamAttempt) -> None:
    """Hamma savolga to'g'ri javob."""
    for question_id in attempt.question_ids:
        question = Question.objects.prefetch_related("choices").get(pk=question_id)
        services.answer_test(attempt, question_id, right(Layout.build(question, attempt.seed)))


def test_single_attempt_from_the_question_pool(world: World) -> None:
    attempt = services.start_test(world.exam, world.student)

    assert len(attempt.question_ids) == 4
    assert set(attempt.question_ids) <= set(services.question_pool(world.exam))
    assert attempt.deadline <= world.exam.closes_at
    assert services.start_test(world.exam, world.student).pk == attempt.pk

    services.finish_test(attempt)
    with pytest.raises(services.ExamError, match="allaqachon"):
        services.start_test(world.exam, world.student)


def test_answers_are_saved_without_verdict(world: World) -> None:
    attempt = services.start_test(world.exam, world.student)
    question = Question.objects.prefetch_related("choices").get(pk=attempt.question_ids[0])

    saved = services.answer_test(attempt, question.pk, right(Layout.build(question, attempt.seed)))
    payload = services.attempt_payload(attempt)

    assert set(saved) == {"question", "response"}
    assert payload["answers"] == [saved]
    assert "correct" not in str(payload)
    with pytest.raises(services.ExamError, match="javob berilgan"):
        services.answer_test(attempt, question.pk, saved["response"])


def test_time_is_kept_on_the_server(world: World) -> None:
    attempt = services.start_test(world.exam, world.student)
    answer_all(attempt)
    ExamAttempt.objects.filter(pk=attempt.pk).update(deadline=timezone.now() - timedelta(seconds=1))
    attempt.refresh_from_db()

    # Javoblar saqlangan, vaqt tugagan — keyingi so'rov testni yakunlaydi.
    with pytest.raises(services.ExamError, match="Vaqt tugadi"):
        services.answer_test(attempt, attempt.question_ids[0], {"choice": 1})
    attempt.refresh_from_db()
    assert attempt.finished_at is not None and attempt.score == 100


def test_overdue_attempts_are_closed_by_beat(world: World) -> None:
    attempt = services.start_test(world.exam, world.student)
    ExamAttempt.objects.filter(pk=attempt.pk).update(deadline=timezone.now() - timedelta(minutes=1))

    assert services.close_overdue() == 1
    attempt.refresh_from_db()
    assert (attempt.score, attempt.finished_at is not None) == (0, True)


def test_closed_exam_opens_again_with_an_extension(world: World) -> None:
    Exam.objects.filter(pk=world.exam.pk).update(closes_at=timezone.now() - timedelta(hours=1))
    world.exam.refresh_from_db()
    with pytest.raises(services.ExamError, match="ochiq emas"):
        services.start_test(world.exam, world.student)

    services.grant_extension(
        world.exam, world.student, timezone.now() + timedelta(days=1), world.teacher
    )

    attempt = services.start_test(world.exam, world.student)
    assert attempt.deadline > timezone.now()


def test_practical_tasks_grading_and_final_result(
    world: World, django_capture_on_commit_callbacks: Any
) -> None:
    attempt = services.start_test(world.exam, world.student)
    answer_all(attempt)
    services.finish_test(attempt)
    first, second = world.tasks
    answer = services.submit_task(first, world.student, text="Tayyor", link="https://example.uz")
    services.submit_task(first, world.student, text="Yangilandi")  # baholanguncha yangilanadi
    services.submit_task(second, world.student, code="<p>salom</p>", language="html")

    services.grade_task(TaskAnswer.objects.get(pk=answer.pk), world.teacher, score=80)
    with pytest.raises(services.ExamError, match="baholangan"):
        services.submit_task(first, world.student, text="Yana")

    # Imtihon ochiq, ikkinchi topshiriq baholanmagan — natija yakuniy emas.
    result = ExamResult.objects.get(exam=world.exam, student=world.student)
    assert (result.test_score, result.practical_score, result.total) == (100, 40, 70)
    assert result.final_at is None

    services.grade_task(
        TaskAnswer.objects.get(task=second, student=world.student), world.teacher, score=100
    )
    Exam.objects.filter(pk=world.exam.pk).update(closes_at=timezone.now() - timedelta(minutes=1))
    with (
        mock.patch("apps.certificates.tasks.check_certificate.delay") as certificate,
        django_capture_on_commit_callbacks(execute=True),
    ):
        assert services.finalize() == 1

    result.refresh_from_db()
    assert (result.practical_score, result.total, result.passed) == (90, 95, True)
    assert result.final_at is not None
    notice = Notification.objects.get(user=world.student, kind=Notification.Kind.EXAM_RESULT)
    assert "95%" in notice.body and notice.link == f"/dashboard/exams/{world.exam.pk}"
    certificate.assert_called_once_with(world.student.pk, world.course.pk)
    assert services.finalize() == 0  # bir marta


def test_review_is_shown_after_the_exam_closes(world: World) -> None:
    from apps.exams import payloads

    attempt = services.start_test(world.exam, world.student)
    answer_all(attempt)
    services.finish_test(attempt)

    during = payloads.detail(world.exam, world.student)["test"]
    Exam.objects.filter(pk=world.exam.pk).update(closes_at=timezone.now() - timedelta(minutes=1))
    world.exam.refresh_from_db()
    after = payloads.detail(world.exam, world.student)["test"]

    assert during["score"] == 100 and during["review"] == []
    assert len(after["review"]) == 4 and all(item["correct"] for item in after["review"])
    assert after["review"][0]["correct_answer"] is not None
    assert len(after["review_questions"]) == 4


def test_monthly_draft_and_opening(world: World, django_capture_on_commit_callbacks: Any) -> None:
    world.exam.delete()
    world.course.monthly_exam = True
    world.course.save()
    with django_capture_on_commit_callbacks(execute=True):
        created = services.create_drafts(today=date(2026, 10, 20))

    exam = Exam.objects.get()
    assert created == 1 and exam.status == Exam.Status.DRAFT
    opens = timezone.localtime(exam.opens_at)
    closes = timezone.localtime(exam.closes_at)
    assert (opens.day, opens.hour) == (25, 0) and (closes.month, closes.day) == (11, 1)
    draft = Notification.objects.get(user=world.teacher, kind=Notification.Kind.EXAM_DRAFT)
    assert draft.link == f"/dashboard/teaching/exams/{exam.pk}"
    assert services.create_drafts(today=date(2026, 10, 20)) == 0

    # Tayyor imtihon ochilganda — qatnashuvchilarga bir marta.
    Exam.objects.filter(pk=exam.pk).update(
        status=Exam.Status.READY,
        opens_at=timezone.now() - timedelta(minutes=5),
        closes_at=timezone.now() + timedelta(days=5),
    )
    with django_capture_on_commit_callbacks(execute=True):
        assert services.announce_open(now=timezone.now()) == 1
        assert services.announce_open(now=timezone.now()) == 0
    opened = Notification.objects.get(user=world.student, kind=Notification.Kind.EXAM_OPENED)
    assert "4 savol" not in opened.body and "20 savol" in opened.body


def test_draft_exam_is_not_open(world: World) -> None:
    Exam.objects.filter(pk=world.exam.pk).update(status=Exam.Status.DRAFT)
    world.exam.refresh_from_db()

    assert not services.available(world.exam, world.student)
    assert services.unready().count() == 1


# --- API ---


def test_student_api_flow(world: World) -> None:
    client = api(world.student)

    [card] = client.get("/api/v1/exams/").json()
    assert (card["state"], card["can_take"], card["tasks_total"]) == ("OPEN", True, 2)
    started = client.post(f"/api/v1/exams/{world.exam.pk}/test/").json()
    assert started["total"] == 4 and started["seconds_left"] > 0
    attempt = ExamAttempt.objects.get()
    question = Question.objects.prefetch_related("choices").get(pk=attempt.question_ids[0])
    saved = client.post(
        f"/api/v1/exam-attempts/{attempt.pk}/answers/",
        {"question": question.pk, "response": right(Layout.build(question, attempt.seed))},
        format="json",
    )
    assert saved.status_code == 200 and "correct" not in saved.json()
    finished = client.post(f"/api/v1/exam-attempts/{attempt.pk}/finish/").json()
    assert finished == {"score": 25}

    upload = SimpleUploadedFile("sahifa.html", b"<p>salom</p>", content_type="text/html")
    response = client.post(
        f"/api/v1/exam-tasks/{world.tasks[0].pk}/answer/",
        {"text": "Mana", "files": [upload]},
        format="multipart",
    )
    assert response.status_code == 201
    task = response.json()["tasks"][0]
    assert task["answer"]["text"] == "Mana" and task["answer"]["files"][0]["name"] == "sahifa.html"
    assert response.json()["tasks_submitted"] == 1


def test_outsider_cannot_see_or_take_the_exam(world: World) -> None:
    stranger = make_user("+998901000009")

    assert api(stranger).get("/api/v1/exams/").json() == []
    assert api(stranger).get(f"/api/v1/exams/{world.exam.pk}/").status_code == 404
    assert api(stranger).post(f"/api/v1/exams/{world.exam.pk}/test/").status_code == 404


def test_teacher_grades_and_extends(world: World) -> None:
    answer = services.submit_task(world.tasks[0], world.student, text="Tayyor")
    client = api(world.teacher)

    [card] = client.get("/api/v1/teacher/exams/").json()
    assert (card["students"], card["to_grade"]) == (1, 1)
    detail = client.get(f"/api/v1/teacher/exams/{world.exam.pk}/").json()
    [row] = detail["rows"]
    assert row["name"] == "Aziz Valiyev" and row["group"] == "FE-1"
    assert row["tasks"][0]["answer"]["text"] == "Tayyor" and row["tasks"][1]["answer"] is None

    graded = client.post(
        f"/api/v1/teacher/exam-answers/{answer.pk}/grade/",
        {"score": 90, "feedback": "Zo'r"},
        format="json",
    )
    assert graded.status_code == 200
    assert graded.json()["rows"][0]["tasks"][0]["answer"]["score"] == 90
    until = (timezone.now() + timedelta(days=3)).isoformat()
    extended = client.put(
        f"/api/v1/teacher/exams/{world.exam.pk}/extensions/",
        {"student": world.student.pk, "until": until},
        format="json",
    )
    assert extended.json()["rows"][0]["extension_until"] is not None

    other = make_user("+998901000003", "TEACHER", name="Boshqa")
    assert api(other).get(f"/api/v1/teacher/exams/{world.exam.pk}/").status_code == 404
    assert (
        api(other)
        .post(f"/api/v1/teacher/exam-answers/{answer.pk}/grade/", {"score": 1}, format="json")
        .status_code
        == 404
    )
