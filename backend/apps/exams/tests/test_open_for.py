"""O'qituvchi imtihonni belgilangan o'quvchilarga ochadi: alohida muddat va xabar."""

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.exams import services
from apps.exams.models import Exam, ExamExtension
from apps.learning.models import Enrollment
from apps.notifications.models import Notification
from apps.users.roles import Role

from .conftest import World, api, make_user

pytestmark = pytest.mark.django_db


def test_teacher_opens_a_closed_exam_for_selected_students(world: World) -> None:
    Exam.objects.filter(pk=world.exam.pk).update(closes_at=timezone.now() - timedelta(hours=1))
    second = make_user("+998901000003", Role.STUDENT, name="Bobur")
    Enrollment.objects.create(user=second, course=world.course, group=world.group)
    stranger = make_user("+998901000004", Role.STUDENT, name="Begona")
    until = timezone.now() + timedelta(days=1)
    url = f"/api/v1/teacher/exams/{world.exam.pk}/open/"

    response = api(world.teacher).post(
        url,
        {"students": [world.student.pk, second.pk, stranger.pk], "until": until.isoformat()},
        format="json",
    )

    assert response.status_code == 200, response.json()
    granted = set(ExamExtension.objects.values_list("student_id", flat=True))
    assert granted == {world.student.pk, second.pk}
    world.exam.refresh_from_db()
    assert services.available(world.exam, second) and not services.available(world.exam, stranger)
    sent = Notification.objects.filter(kind=Notification.Kind.EXAM_OPENED)
    assert sent.count() == 2 and all("gacha topshiring" in item.body for item in sent)
    rows = {row["student_id"]: row for row in response.json()["rows"]}
    assert rows[second.pk]["extension_until"] is not None

    only_strangers = api(world.teacher).post(
        url, {"students": [stranger.pk], "until": until.isoformat()}, format="json"
    )
    assert only_strangers.status_code == 404


def test_draft_exam_is_not_opened(world: World, capsys: Any) -> None:
    Exam.objects.filter(pk=world.exam.pk).update(status=Exam.Status.DRAFT)
    until = timezone.now() + timedelta(days=1)

    response = api(world.teacher).post(
        f"/api/v1/teacher/exams/{world.exam.pk}/open/",
        {"students": [world.student.pk], "until": until.isoformat()},
        format="json",
    )

    assert response.status_code == 400 and not ExamExtension.objects.exists()
