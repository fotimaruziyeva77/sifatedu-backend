"""Admin: imtihon topshiriqsiz yoki savolsiz «Tayyor» bo'lmaydi; oyna o'zi to'ldiriladi."""

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.exams.models import Exam
from apps.users.roles import Role

from .conftest import World, make_user

pytestmark = pytest.mark.django_db


def form(world: World, **extra: Any) -> dict[str, Any]:
    return {
        "course": world.course.pk,
        "month": "2027-01-15",
        "status": Exam.Status.READY,
        "questions_count": 20,
        "duration_min": 40,
        "pass_percent": 60,
        "test_weight": 50,
        "opens_at_0": "",
        "opens_at_1": "",
        "closes_at_0": "",
        "closes_at_1": "",
        "tasks-TOTAL_FORMS": "0",
        "tasks-INITIAL_FORMS": "0",
        "tasks-MIN_NUM_FORMS": "0",
        "tasks-MAX_NUM_FORMS": "5",
        **extra,
    }


@pytest.fixture
def client(world: World) -> Client:
    manager = make_user("+998901000005", Role.MANAGER, name="Menejer")
    browser = Client()
    browser.force_login(manager)
    return browser


def test_exam_without_tasks_stays_a_draft(world: World, client: Client) -> None:
    response = client.post(reverse("admin:exams_exam_add"), form(world), follow=True)

    exam = Exam.objects.get(month="2027-01-01")
    assert response.status_code == 200 and exam.status == Exam.Status.DRAFT
    assert "amaliy topshiriq yo" in response.content.decode()
    opens = timezone.localtime(exam.opens_at)
    assert (opens.month, opens.day, opens.hour) == (1, 25, 0)


def test_exam_with_tasks_and_questions_is_ready(world: World, client: Client) -> None:
    data = form(
        world,
        **{
            "tasks-TOTAL_FORMS": "1",
            "tasks-0-order": "1",
            "tasks-0-title": "Portfolio sahifasi",
            "tasks-0-instructions": "Bitta sahifa",
        },
    )

    client.post(reverse("admin:exams_exam_add"), data)

    exam = Exam.objects.get(month="2027-01-01")
    assert exam.status == Exam.Status.READY and exam.tasks.count() == 1
