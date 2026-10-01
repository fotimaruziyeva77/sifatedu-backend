"""Kabinet: mening kurslarim, kurs dasturi va bepul kursni boshlash."""

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, Lesson, Module
from apps.learning.models import Enrollment, LessonProgress
from apps.users.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def student(db: Any) -> User:
    return User.objects.create_user(phone="+998901112233", password="Parol12345")


def make_course(slug: str, *, lessons: int = 2, **extra: Any) -> Course:
    category, _ = Category.objects.get_or_create(slug="dasturlash", defaults={"name_uz": "D"})
    course = Course.objects.create(
        slug=slug,
        title_uz=slug.title(),
        category=category,
        status=Course.Status.PUBLISHED,
        **extra,
    )
    module = Module.objects.create(course=course, title_uz="Modul")
    for index in range(lessons):
        Lesson.objects.create(
            module=module, title_uz=f"Dars {index + 1}", order=index, duration_min=20
        )
    return course


def test_my_courses_is_empty_without_enrollment(client: APIClient, student: User) -> None:
    make_course("frontend")
    client.force_authenticate(student)

    assert client.get("/api/v1/my/courses/").json() == []


def test_my_courses_requires_login(client: APIClient) -> None:
    assert client.get("/api/v1/my/courses/").status_code == 403


def test_my_courses_shows_progress(client: APIClient, student: User) -> None:
    course = make_course("frontend", lessons=4)
    Enrollment.objects.create(user=student, course=course)
    lessons = list(Lesson.objects.filter(module__course=course).order_by("order"))
    LessonProgress.objects.create(
        user=student, lesson=lessons[0], position_sec=1200, completed_at="2026-09-27T10:00:00Z"
    )
    client.force_authenticate(student)

    card = client.get("/api/v1/my/courses/").json()[0]

    assert card["slug"] == "frontend"
    assert (card["completed_count"], card["lesson_count"]) == (1, 4)
    assert card["percent"] == 25
    # "Davom ettirish" tugatilmagan birinchi darsga olib boradi.
    assert card["next_lesson_id"] == lessons[1].pk


def test_my_course_program_marks_locked_lessons(client: APIClient, student: User) -> None:
    course = make_course("frontend", lessons=2)
    Lesson.objects.filter(module__course=course, order=0).update(is_preview=True)
    client.force_authenticate(student)

    # Yozilmagan: kurs sahifasi ochilmaydi.
    assert client.get("/api/v1/my/courses/frontend/").status_code == 403

    Enrollment.objects.create(user=student, course=course)
    payload = client.get("/api/v1/my/courses/frontend/").json()

    lessons = payload["modules"][0]["lessons"]
    assert [lesson["locked"] for lesson in lessons] == [False, False]
    assert [lesson["has_video"] for lesson in lessons] == [False, False]


def test_free_course_enroll_creates_access(client: APIClient, student: User) -> None:
    make_course("bepul", is_free=True, price_online=0)
    client.force_authenticate(student)

    response = client.post("/api/v1/my/courses/bepul/enroll/")

    assert response.status_code == 201
    enrollment = Enrollment.objects.get(user=student, course__slug="bepul")
    assert enrollment.source == Enrollment.Source.FREE
    assert enrollment.is_open
    assert client.get("/api/v1/my/courses/").json()[0]["slug"] == "bepul"


def test_paid_course_cannot_be_enrolled_for_free(client: APIClient, student: User) -> None:
    make_course("frontend", price_online=1_800_000)
    client.force_authenticate(student)

    response = client.post("/api/v1/my/courses/frontend/enroll/")

    assert response.status_code == 400
    assert not Enrollment.objects.exists()


def test_enroll_twice_is_safe(client: APIClient, student: User) -> None:
    make_course("bepul", is_free=True)
    client.force_authenticate(student)

    client.post("/api/v1/my/courses/bepul/enroll/")
    client.post("/api/v1/my/courses/bepul/enroll/")

    assert Enrollment.objects.filter(user=student).count() == 1


def test_kids_course_keeps_audience_in_payload(client: APIClient, student: User) -> None:
    course = make_course("sifat-kids", audience=Course.Audience.KIDS, age_min=7, age_max=11)
    Enrollment.objects.create(user=student, course=course)
    client.force_authenticate(student)

    card = client.get("/api/v1/my/courses/").json()[0]

    assert card["audience"] == Course.Audience.KIDS


def test_paid_offline_course_is_premium_with_its_own_format(
    client: APIClient, student: User
) -> None:
    course = make_course("backend", study_format=Course.Format.BOTH)
    Enrollment.objects.create(
        user=student,
        course=course,
        source=Enrollment.Source.PAYMENT,
        study_format=Enrollment.Format.OFFLINE,
    )
    client.force_authenticate(student)

    card = client.get("/api/v1/my/courses/").json()[0]

    assert card["is_premium"] is True
    # Kurs ikkala shaklda, lekin o'quvchi offlaynni sotib olgan — kabinetda shu ko'rinadi.
    assert card["study_format"] == Enrollment.Format.OFFLINE


def test_manual_enrollment_is_not_premium(client: APIClient, student: User) -> None:
    Enrollment.objects.create(user=student, course=make_course("frontend"))
    client.force_authenticate(student)

    assert client.get("/api/v1/my/courses/").json()[0]["is_premium"] is False
