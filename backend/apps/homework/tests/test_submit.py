"""O'quvchi: javob yuborish, fayl cheklovlari, urinishlar, qaytarib olish, "Vazifalar" ro'yxati."""

from datetime import timedelta
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.homework import files
from apps.homework.models import Assignment, Submission, SubmissionFile
from apps.learning.models import LessonProgress
from apps.notifications.models import Notification

from .conftest import World, api, make_user, png

pytestmark = pytest.mark.django_db


def url(world: World) -> str:
    return f"/api/v1/homework/{world.assignment.pk}/submissions/"


def test_submit_with_code_link_and_files(
    world: World, django_capture_on_commit_callbacks: Any
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        response = api(world.student).post(
            url(world),
            {
                "text": "Tayyor!",
                "code": "<h1>Salom</h1>",
                "language": "html",
                "link": "https://github.com/aziz/sahifa",
                "files": [
                    png(),
                    SimpleUploadedFile("loyiha.zip", b"PK\x03\x04", "application/zip"),
                ],
            },
            format="multipart",
        )

    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["status"] == Submission.Status.SUBMITTED
    [attempt] = body["attempts"]
    assert attempt["attempt"] == 1 and attempt["code"] == "<h1>Salom</h1>"
    assert [item["name"] for item in attempt["files"]] == ["rasm.png", "loyiha.zip"]
    assert [item["is_image"] for item in attempt["files"]] == [True, False]
    # Guruh ustoziga xabar ketdi.
    note = Notification.objects.get(user=world.teacher)
    assert note.kind == Notification.Kind.HOMEWORK_SUBMITTED
    assert note.link == f"/dashboard/reviews/{attempt['id']}"


def test_lesson_payload_includes_homework(world: World) -> None:
    lesson = world.assignment.lesson

    body = api(world.student).get(f"/api/v1/lessons/{lesson.pk}/").json()

    assert body["homework"]["title"] == "Sahifa"
    assert body["homework"]["status"] == "NOT_SUBMITTED"
    assert (
        api(world.student).get(f"/api/v1/lessons/{world.lessons[1].pk}/").json()["homework"] is None
    )


def test_empty_answer_and_bad_files_are_rejected(world: World) -> None:
    client = api(world.student)

    empty = client.post(url(world), {"text": "  "}, format="multipart")
    program = client.post(
        url(world),
        {"files": [SimpleUploadedFile("virus.exe", b"MZ", "application/octet-stream")]},
        format="multipart",
    )
    fake_image = client.post(
        url(world),
        {"files": [SimpleUploadedFile("rasm.png", b"<html>", "image/png")]},
        format="multipart",
    )
    too_many = client.post(
        url(world),
        {"files": [png(f"r{index}.png") for index in range(files.MAX_FILES + 1)]},
        format="multipart",
    )

    assert empty.status_code == 400
    assert program.status_code == 400 and "qabul qilinmaydi" in str(program.json())
    assert fake_image.status_code == 400 and "rasm sifatida" in str(fake_image.json())
    assert too_many.status_code == 400
    assert not Submission.objects.exists()


def test_file_size_limit(world: World, monkeypatch: Any) -> None:
    monkeypatch.setattr(files, "MAX_FILE_BYTES", 10)

    response = api(world.student).post(
        url(world),
        {"files": [SimpleUploadedFile("kod.py", b"print('salom dunyo')", "text/x-python")]},
        format="multipart",
    )

    assert response.status_code == 400 and "juda katta" in str(response.json())


def test_attempts_follow_review(world: World) -> None:
    client = api(world.student)
    client.post(url(world), {"text": "1"}, format="multipart")

    while_pending = client.post(url(world), {"text": "2"}, format="multipart")
    Submission.objects.update(status=Submission.Status.CHANGES_REQUESTED, feedback="Tuzating")
    second = client.post(url(world), {"text": "2"}, format="multipart")
    Submission.objects.filter(attempt=2).update(status=Submission.Status.ACCEPTED, score=90)
    after_accept = client.post(url(world), {"text": "3"}, format="multipart")

    assert while_pending.status_code == 400 and "tekshirilmoqda" in str(while_pending.json())
    assert second.status_code == 201
    assert [item["attempt"] for item in second.json()["attempts"]] == [2, 1]
    assert after_accept.status_code == 400


def test_late_submission_is_marked(world: World) -> None:
    Assignment.objects.filter(pk=world.assignment.pk).update(
        deadline=timezone.now() - timedelta(days=1)
    )

    api(world.student).post(url(world), {"text": "Kechikdim"}, format="multipart")

    assert Submission.objects.get().late is True


def test_withdraw_pending_only(world: World, django_capture_on_commit_callbacks: Any) -> None:
    client = api(world.student)
    with django_capture_on_commit_callbacks(execute=True):
        client.post(url(world), {"text": "1", "files": [png()]}, format="multipart")
    submission = Submission.objects.get()

    other = api(make_user("+998901000009")).delete(f"/api/v1/homework/submissions/{submission.pk}/")
    with django_capture_on_commit_callbacks(execute=True):
        mine = client.delete(f"/api/v1/homework/submissions/{submission.pk}/")

    assert other.status_code == 404
    assert mine.status_code == 204
    assert not Submission.objects.exists() and not SubmissionFile.objects.exists()


def test_students_without_access_cannot_submit(world: World) -> None:
    stranger = make_user("+998901000010")

    response = api(stranger).post(url(world), {"text": "Salom"}, format="multipart")

    assert response.status_code == 403


def test_my_homework_shows_reached_lessons(world: World) -> None:
    later = Assignment.objects.create(lesson=world.lessons[2], instructions="Keyinroq")
    client = api(world.student)

    before = client.get("/api/v1/homework/").json()
    LessonProgress.objects.create(user=world.student, lesson=world.lessons[1], position_sec=5)
    after = client.get("/api/v1/homework/").json()

    # Boshida — faqat birinchi vazifa; 2-darsga yetgach, 3-dars vazifasi ham ko'rinadi.
    assert [item["assignment_id"] for item in before] == [world.assignment.pk]
    assert {item["assignment_id"] for item in after} == {world.assignment.pk, later.pk}
    assert after[0]["status"] == "NOT_SUBMITTED"
