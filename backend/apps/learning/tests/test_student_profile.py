"""O'qituvchi o'quvchi profilini tuzatadi: to'liq ism, tug'ilgan sana va rasm (22d)."""

import io
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course
from apps.learning.models import Enrollment, StudyGroup
from apps.users.models import User
from apps.users.roles import Role, set_roles

pytestmark = pytest.mark.django_db


def user_with(phone: str, *roles: str, name: str = "") -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name=name)
    set_roles(user, roles)
    return user


def api(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def photo(name: str = "selfi.jpg") -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (1200, 900), "#3a6ea5").save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


@pytest.fixture
def group(db: Any) -> StudyGroup:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="python", title_uz="Python", category=category)
    teacher = user_with("+998903000001", Role.TEACHER, name="Ustoz")
    group = StudyGroup.objects.create(
        course=course, teacher=teacher, name="Python", status=StudyGroup.Status.ACTIVE
    )
    student = user_with("+998901000001", Role.STUDENT, name="❤️ALHAMDULILLAH❤️👍")
    Enrollment.objects.create(user=student, course=course, group=group)
    return group


def url(group: StudyGroup, user: User) -> str:
    return f"/api/v1/teacher/groups/{group.pk}/students/{user.pk}/"


def test_teacher_sets_real_name_birth_date_and_photo(group: StudyGroup) -> None:
    student = User.objects.get(phone="+998901000001")
    client = api(group.teacher)
    before = client.get(f"/api/v1/teacher/groups/{group.pk}/").json()["students"][0]
    assert (before["profile_complete"], before["birth_date"], before["middle_name"]) == (
        False,
        None,
        "",
    )

    response = client.patch(
        url(group, student),
        {
            "first_name": "Aziz",
            "last_name": "Valiyev",
            "middle_name": "Akmal o'g'li",
            "birth_date": "2008-03-14",
            "photo": photo(),
        },
        format="multipart",
    )

    assert response.status_code == 200, response.json()
    body = response.json()
    assert (body["name"], body["birth_date"], body["profile_complete"]) == (
        "Aziz Valiyev",
        "2008-03-14",
        True,
    )
    student.refresh_from_db()
    with student.avatar.open("rb") as handle, Image.open(handle) as saved:
        assert saved.size == (512, 512)
    row = client.get(f"/api/v1/teacher/groups/{group.pk}/").json()["students"][0]
    assert (row["name"], row["middle_name"], row["avatar"] != "") == (
        "Aziz Valiyev",
        "Akmal o'g'li",
        True,
    )

    cleared = client.patch(
        url(group, student),
        {"first_name": "Aziz", "last_name": "Valiyev", "birth_date": "", "remove_photo": "true"},
        format="multipart",
    )
    assert cleared.status_code == 200, cleared.json()
    assert (cleared.json()["avatar"], cleared.json()["birth_date"]) == ("", None)


def test_wrong_data_and_strangers_are_refused(group: StudyGroup) -> None:
    student = User.objects.get(phone="+998901000001")
    client = api(group.teacher)

    future = client.patch(
        url(group, student), {"first_name": "Aziz", "birth_date": "2030-01-01"}, format="multipart"
    )
    junk = client.patch(
        url(group, student),
        {"first_name": "Aziz", "photo": SimpleUploadedFile("a.jpg", b"not an image")},
        format="multipart",
    )
    nameless = client.patch(url(group, student), {"first_name": " "}, format="multipart")
    stranger = api(user_with("+998903000002", Role.TEACHER, name="Boshqa")).patch(
        url(group, student), {"first_name": "Aziz"}, format="multipart"
    )
    manager = api(user_with("+998903000003", Role.MANAGER, name="Menejer")).patch(
        url(group, student), {"first_name": "Aziz", "last_name": "Valiyev"}, format="multipart"
    )
    outsider = user_with("+998901000009", Role.STUDENT, name="Begona")

    assert future.status_code == 400 and "birth_date" in future.json()["error"]["fields"]
    assert junk.status_code == 400 and "photo" in junk.json()["error"]["fields"]
    assert nameless.status_code == 400
    assert stranger.status_code == 404
    assert manager.status_code == 200
    assert client.patch(url(group, outsider), {"first_name": "X"}).status_code == 404
