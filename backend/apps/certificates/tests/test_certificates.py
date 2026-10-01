"""Sertifikat: shartlar, avtomatik berish, offlayn guruh, imtihon o'rtachasi, tekshirish, bekor
qilish."""

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.certificates import services
from apps.certificates.models import Certificate
from apps.core import events
from apps.exams.models import ExamResult
from apps.exams.tests.conftest import World, api, make_user
from apps.learning.models import LessonProgress
from apps.live.models import GroupLesson
from apps.notifications.models import Notification
from apps.quizzes.models import Attempt
from apps.users.roles import Role

pytestmark = pytest.mark.django_db


def complete_lessons(world: World) -> None:
    now = timezone.now()
    for lesson in world.lessons:
        LessonProgress.objects.create(user=world.student, lesson=lesson, completed_at=now)


def pass_quiz(world: World, score: int = 90) -> None:
    Attempt.objects.create(
        quiz=world.quiz,
        student=world.student,
        score=score,
        passed=True,
        finished_at=timezone.now(),
    )


def codes(world: World) -> dict[str, tuple[int, int]]:
    return {
        item.code: (item.done, item.total)
        for item in services.requirements(world.student, world.course)
    }


def test_certificate_is_issued_when_everything_is_done(world: World) -> None:
    assert codes(world) == {"lessons": (0, 2), "quizzes": (0, 1), "homework": (0, 0)}
    assert services.check(world.student.pk, world.course.pk) is None

    complete_lessons(world)
    pass_quiz(world)
    certificate = services.check(world.student.pk, world.course.pk)

    assert certificate is not None and certificate.is_valid
    assert certificate.number.startswith(f"SE-{timezone.now():%y%m}-")
    assert (certificate.full_name, certificate.score) == ("Aziz Valiyev", 90)
    notice = Notification.objects.get(user=world.student, kind=Notification.Kind.CERTIFICATE)
    assert certificate.number in notice.body and notice.link == "/dashboard/certificates"
    assert services.check(world.student.pk, world.course.pk) is None  # bir marta


def test_exam_average_must_reach_the_pass_mark(world: World) -> None:
    complete_lessons(world)
    pass_quiz(world)
    result = ExamResult.objects.create(
        exam=world.exam, student=world.student, total=50, final_at=timezone.now()
    )

    assert codes(world)["exams"] == (50, 60)
    assert services.check(world.student.pk, world.course.pk) is None

    ExamResult.objects.filter(pk=result.pk).update(total=80)
    certificate = services.check(world.student.pk, world.course.pk)
    assert certificate is not None and certificate.score == 85  # (test 90 + imtihon 80) / 2


def test_offline_group_counts_lessons_covered_in_class(world: World) -> None:
    world.group.study_format = "OFFLINE"
    world.group.save()
    pass_quiz(world)
    assert codes(world)["lessons"] == (0, 2)

    GroupLesson.objects.create(group=world.group, lesson=world.lessons[1])

    assert codes(world)["lessons"] == (2, 2)
    assert services.check(world.student.pk, world.course.pk) is not None


def test_course_without_certificate_and_staff_get_none(world: World) -> None:
    complete_lessons(world)
    pass_quiz(world)
    world.course.certificate = False
    world.course.save()

    assert services.check(world.student.pk, world.course.pk) is None
    assert services.check(world.teacher.pk, world.course.pk) is None


def test_learning_events_issue_the_certificate(
    world: World, django_capture_on_commit_callbacks: Any
) -> None:
    complete_lessons(world)
    pass_quiz(world)

    with django_capture_on_commit_callbacks(execute=True):
        events.quiz_passed.send(sender=Attempt, user_id=world.student.pk, course_id=world.course.pk)

    assert Certificate.objects.filter(user=world.student, course=world.course).exists()


def test_my_certificates_and_public_verification(world: World) -> None:
    progress = api(world.student).get("/api/v1/certificates/").json()
    assert progress["certificates"] == []
    [course] = progress["progress"]
    assert course["course_title"] == "Frontend"
    assert {item["code"]: item["ok"] for item in course["requirements"]} == {
        "lessons": False,
        "quizzes": False,
        "homework": True,
    }

    complete_lessons(world)
    pass_quiz(world)
    certificate = services.check(world.student.pk, world.course.pk)
    assert certificate is not None
    mine = api(world.student).get("/api/v1/certificates/").json()
    assert [item["number"] for item in mine["certificates"]] == [certificate.number]
    assert mine["progress"] == []

    public = api().get(f"/api/v1/certificates/{certificate.number.lower()}/")
    assert public.status_code == 200
    assert public.json()["full_name"] == "Aziz Valiyev" and public.json()["valid"] is True
    assert api().get("/api/v1/certificates/SE-0000-XXXXXX/").status_code == 404


def test_admin_revokes_and_restores(world: World) -> None:
    complete_lessons(world)
    pass_quiz(world)
    certificate = services.check(world.student.pk, world.course.pk)
    assert certificate is not None
    manager = make_user("+998901000005", Role.MANAGER, name="Menejer")
    client = Client()
    client.force_login(manager)

    page = client.get(reverse("admin:certificates_certificate_change", args=[certificate.pk]))
    revoked = client.post(
        reverse("admin:certificates_certificate_revoke", args=[certificate.pk]),
        {"_form_submitted": "True", "reason": "Ko'chirilgan ish"},
        HTTP_HX_REQUEST="true",
    )

    assert page.status_code == 200 and revoked.status_code in (200, 302)
    certificate.refresh_from_db()
    assert not certificate.is_valid and certificate.revoke_reason == "Ko'chirilgan ish"
    public = api().get(f"/api/v1/certificates/{certificate.number}/").json()
    assert (public["valid"], public["revoke_reason"]) == (False, "Ko'chirilgan ish")

    client.post(
        reverse("admin:certificates_certificate_restore", args=[certificate.pk]),
        HTTP_HX_REQUEST="true",
    )
    certificate.refresh_from_db()
    assert certificate.is_valid
