"""Admin va menejer saytdagi kabinetda barcha guruhlarni o'qituvchi kabi boshqaradi; o'qituvchi —
faqat o'zinikini; direktor kabinetga kirmaydi (unga admin paneldagi statistika)."""

from datetime import time
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course
from apps.learning.models import Enrollment, StudyGroup
from apps.live.models import ScheduleSlot
from apps.users.models import User
from apps.users.roles import Role, set_roles

pytestmark = pytest.mark.django_db

URL = "/api/v1/teacher/groups/"


def person(phone: str, *roles: str, name: str = "") -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name=name)
    set_roles(user, roles)
    return user


def api(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def groups(db: Any) -> list[StudyGroup]:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="python", title_uz="Python", category=category)
    return [
        StudyGroup.objects.create(
            course=course,
            teacher=person(phone, Role.TEACHER, name=name),
            name=group,
            status=StudyGroup.Status.ACTIVE,
        )
        for phone, name, group in (
            ("+998903000001", "Ustoz", "Python-1"),
            ("+998903000002", "Murabbiy", "Python-2"),
        )
    ]


@pytest.mark.parametrize("role", [Role.ADMIN, Role.MANAGER])
def test_admin_and_manager_see_every_group_with_its_teacher(
    groups: list[StudyGroup], role: str
) -> None:
    response = api(person("+998909000001", role)).get(URL)

    assert response.status_code == 200
    assert [(card["name"], card["teacher_name"]) for card in response.json()] == [
        ("Python-1", "Ustoz"),
        ("Python-2", "Murabbiy"),
    ]


def test_teacher_still_sees_only_own_groups(groups: list[StudyGroup]) -> None:
    client = api(groups[0].teacher)

    assert [card["name"] for card in client.get(URL).json()] == ["Python-1"]
    assert client.get(f"{URL}{groups[1].pk}/").status_code == 404


def test_manager_runs_any_group_like_its_teacher(groups: list[StudyGroup]) -> None:
    client = api(person("+998909000001", Role.MANAGER))
    group = groups[1]

    added = client.post(
        f"{URL}{group.pk}/students/", {"phone": "901234567", "first_name": "Jahongir"}
    )
    slot = client.post(
        f"{URL}{group.pk}/slots/", {"weekday": 0, "starts_at": "18:00", "duration_min": 90}
    )

    assert added.status_code == 201, added.json()
    assert slot.status_code == 201, slot.json()
    student = User.objects.get(phone="+998901234567")
    assert Enrollment.objects.get(user=student).group == group
    assert ScheduleSlot.objects.get(group=group).starts_at == time(18, 0)
    removed = client.delete(f"{URL}{group.pk}/students/{student.pk}/")
    assert removed.status_code == 200
    assert Enrollment.objects.get(user=student).status == Enrollment.Status.CANCELLED


def test_director_has_no_group_cabinet(groups: list[StudyGroup]) -> None:
    client = api(person("+998909000001", Role.DIRECTOR))

    assert client.get(URL).status_code == 403
    assert client.get(f"{URL}{groups[0].pk}/").status_code == 403
