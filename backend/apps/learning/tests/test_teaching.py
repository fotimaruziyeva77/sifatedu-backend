"""O'qituvchi kabineti va guruhlar: faqat o'z guruhlari, progress, guruh va kurs mosligi."""

from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, Lesson, Module
from apps.learning.models import Enrollment, LessonProgress, StudyGroup
from apps.users.models import User
from apps.users.roles import Role, set_roles

pytestmark = pytest.mark.django_db

URL = "/api/v1/teacher/groups/"


def user_with(phone: str, *roles: str, name: str = "") -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name=name)
    set_roles(user, roles)
    return user


@pytest.fixture
def course(db: Any) -> Course:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="frontend", title_uz="Frontend", category=category)
    module = Module.objects.create(course=course, title_uz="HTML")
    for index in range(4):
        Lesson.objects.create(module=module, title_uz=f"Dars {index}", order=index)
    return course


@pytest.fixture
def teacher(db: Any) -> User:
    return user_with("+998903000001", Role.TEACHER, name="Ustoz")


def enroll(course: Course, phone: str, name: str, group: StudyGroup | None = None) -> Enrollment:
    student = user_with(phone, Role.STUDENT, name=name)
    return Enrollment.objects.create(user=student, course=course, group=group)


def complete(enrollment: Enrollment, count: int) -> None:
    for lesson in Lesson.objects.filter(module__course=enrollment.course).order_by("order")[:count]:
        LessonProgress.objects.create(
            user=enrollment.user, lesson=lesson, position_sec=60, completed_at=timezone.now()
        )


def test_teacher_sees_own_groups_with_progress(course: Course, teacher: User) -> None:
    group = StudyGroup.objects.create(
        course=course, teacher=teacher, name="FE-1", status=StudyGroup.Status.ACTIVE
    )
    ahead = enroll(course, "+998903000002", "Aziz", group)
    behind = enroll(course, "+998903000003", "Bekzod", group)
    complete(ahead, 3)
    complete(behind, 1)
    other_teacher = user_with("+998903000004", Role.TEACHER)
    StudyGroup.objects.create(course=course, teacher=other_teacher, name="FE-2")
    client = APIClient()
    client.force_authenticate(teacher)

    [card] = client.get(URL).json()
    detail = client.get(f"{URL}{group.pk}/").json()

    assert card["name"] == "FE-1" and card["students_count"] == 2
    assert card["average_percent"] == 50  # (75 + 25) / 2
    # Orqada qolgan o'quvchi birinchi: yordam kerak bo'lganlar tepada.
    assert [student["name"] for student in detail["students"]] == ["Bekzod", "Aziz"]
    assert detail["students"][0]["completed"] == 1 and detail["students"][0]["total"] == 4
    assert detail["students"][0]["last_activity"] is not None
    assert detail["students"][0]["inactive"] is False


def test_other_teachers_group_is_hidden(course: Course, teacher: User) -> None:
    other_teacher = user_with("+998903000005", Role.TEACHER)
    foreign = StudyGroup.objects.create(course=course, teacher=other_teacher, name="FE-3")
    client = APIClient()
    client.force_authenticate(teacher)

    assert client.get(f"{URL}{foreign.pk}/").status_code == 404


def test_students_cannot_open_teacher_api(course: Course) -> None:
    client = APIClient()
    client.force_authenticate(user_with("+998903000006", Role.STUDENT))

    assert client.get(URL).status_code == 403
    assert APIClient().get(URL).status_code == 403


def test_enrollment_group_must_match_course(course: Course, teacher: User) -> None:
    other = Course.objects.create(slug="backend", title_uz="Backend", category=course.category)
    group = StudyGroup.objects.create(course=other, teacher=teacher, name="BE-1")
    enrollment = enroll(course, "+998903000007", "Dilnoza")
    enrollment.group = group

    with pytest.raises(ValidationError):
        enrollment.full_clean()


def test_manager_assigns_students_in_group_form(course: Course, teacher: User) -> None:
    group = StudyGroup.objects.create(course=course, teacher=teacher, name="FE-4")
    first = enroll(course, "+998903000008", "Aziz")
    second = enroll(course, "+998903000009", "Bekzod", group)
    manager = user_with("+998903000010", Role.MANAGER)
    client = Client()
    client.force_login(manager)

    response = client.post(
        reverse("admin:learning_studygroup_change", args=[group.pk]),
        {
            "name": "FE-4",
            "course": course.pk,
            "teacher": teacher.pk,
            "study_format": "OFFLINE",
            "status": StudyGroup.Status.ACTIVE,
            "students": [first.pk],
            # Guruh sahifasidagi jadval va o'tilgan darslar (bo'sh).
            **{
                f"{prefix}-{key}": value
                for prefix in ("slots", "covered_lessons")
                for key, value in (
                    ("TOTAL_FORMS", "0"),
                    ("INITIAL_FORMS", "0"),
                    ("MIN_NUM_FORMS", "0"),
                    ("MAX_NUM_FORMS", "1000"),
                )
            },
        },
    )

    assert response.status_code == 302
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.group == group and second.group is None


def test_teacher_admin_lists_only_own_groups(course: Course, teacher: User) -> None:
    StudyGroup.objects.create(course=course, teacher=teacher, name="Mine")
    StudyGroup.objects.create(
        course=course, teacher=user_with("+998903000011", Role.TEACHER), name="Theirs"
    )
    client = Client()
    client.force_login(teacher)

    page = client.get(reverse("admin:learning_studygroup_changelist"))

    assert [group.name for group in page.context["cl"].result_list] == ["Mine"]
