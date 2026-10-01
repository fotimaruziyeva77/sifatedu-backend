"""Admin panel rollar bo'yicha: kim nimani ko'radi va o'zgartiradi (TZ 3.2)."""

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Category, Course, Instructor, Lesson, Module
from apps.leads.models import Lead
from apps.users.models import User
from apps.users.roles import Role, role_names, set_roles

pytestmark = pytest.mark.django_db


def login_as(phone: str, *roles: str) -> tuple[Client, User]:
    user = User.objects.create_user(phone=phone, password="Str0ng-pass", first_name=phone[-4:])
    set_roles(user, roles)
    client = Client()
    client.force_login(user)
    return client, user


@pytest.fixture
def catalog(db: Any) -> dict[str, Any]:
    category = Category.objects.create(slug="it", name_uz="IT")
    mine = Course.objects.create(slug="mine", title_uz="Mening kursim", category=category)
    other = Course.objects.create(slug="other", title_uz="Boshqa kurs", category=category)
    my_module = Module.objects.create(course=mine, title_uz="Modul A")
    other_module = Module.objects.create(course=other, title_uz="Modul B")
    return {
        "mine": mine,
        "other": other,
        "my_lesson": Lesson.objects.create(module=my_module, title_uz="Dars A"),
        "other_lesson": Lesson.objects.create(module=other_module, title_uz="Dars B"),
        "other_module": other_module,
    }


def teach(course: Course, teacher: User) -> None:
    profile = Instructor.objects.create(slug=f"t-{teacher.pk}", full_name="Ustoz", user=teacher)
    course.instructors.add(profile)


@pytest.mark.parametrize(
    ("role", "url_name", "status"),
    [
        (Role.MANAGER, "admin:leads_lead_changelist", 200),
        (Role.MANAGER, "admin:learning_studygroup_add", 200),
        (Role.MANAGER, "admin:catalog_course_add", 403),
        (Role.MANAGER, "admin:content_sitesettings_changelist", 403),
        (Role.DIRECTOR, "admin:leads_lead_changelist", 200),
        (Role.DIRECTOR, "admin:payments_order_changelist", 200),
        (Role.DIRECTOR, "admin:leads_lead_add", 403),
        (Role.TEACHER, "admin:catalog_lesson_changelist", 200),
        (Role.TEACHER, "admin:leads_lead_changelist", 403),
        (Role.TEACHER, "admin:payments_order_changelist", 403),
        (Role.TEACHER, "admin:users_user_changelist", 403),
    ],
)
def test_admin_access_matrix(role: str, url_name: str, status: int) -> None:
    client, _user = login_as("+998902000001", role)

    assert client.get(reverse(url_name)).status_code == status


def test_student_cannot_open_admin() -> None:
    client, _user = login_as("+998902000002", Role.STUDENT)

    response = client.get(reverse("admin:index"))

    assert response.status_code == 302 and "/login/" in response["Location"]


def test_director_sees_but_cannot_change() -> None:
    lead = Lead.objects.create(name="Ali", phone="+998901112233")
    client, _user = login_as("+998902000003", Role.DIRECTOR)

    page = client.get(reverse("admin:leads_lead_change", args=[lead.pk]))
    post = client.post(reverse("admin:leads_lead_change", args=[lead.pk]), {"name": "X"})

    assert page.status_code == 200 and not page.context["has_change_permission"]
    assert post.status_code == 403


def test_teacher_sees_only_own_courses(catalog: dict[str, Any]) -> None:
    client, teacher = login_as("+998902000004", Role.TEACHER)
    teach(catalog["mine"], teacher)

    lessons = client.get(reverse("admin:catalog_lesson_changelist"))
    foreign = client.get(reverse("admin:catalog_lesson_change", args=[catalog["other_lesson"].pk]))

    listed = {lesson.pk for lesson in lessons.context["cl"].result_list}
    assert listed == {catalog["my_lesson"].pk}
    # Ro'yxatda yo'q yozuv — "topilmadi" (admin bosh sahifasiga qaytaradi).
    assert foreign.status_code == 302


def test_teacher_cannot_add_lesson_to_foreign_module(catalog: dict[str, Any]) -> None:
    client, teacher = login_as("+998902000005", Role.TEACHER)
    teach(catalog["mine"], teacher)

    response = client.post(
        reverse("admin:catalog_lesson_add"),
        {
            "module": catalog["other_module"].pk,
            "title_uz": "Begona dars",
            "duration_min": 10,
            "materials-TOTAL_FORMS": 0,
            "materials-INITIAL_FORMS": 0,
        },
    )

    assert response.status_code == 200  # forma xato bilan qaytdi
    assert "module" in response.context["adminform"].form.errors
    assert not Lesson.objects.filter(title_uz="Begona dars").exists()


def test_manager_edits_students_but_not_staff() -> None:
    client, _manager = login_as("+998902000006", Role.MANAGER)
    student = User.objects.create_user(phone="+998902000007", password="x")
    teacher = User.objects.create_user(phone="+998902000008", password="x")
    set_roles(teacher, [Role.TEACHER])

    student_page = client.get(reverse("admin:users_user_change", args=[student.pk]))
    staff_post = client.post(reverse("admin:users_user_change", args=[teacher.pk]), {})

    assert student_page.status_code == 200
    # Menejer rol bera olmaydi: maydon formada yo'q.
    assert "roles" not in student_page.context["adminform"].form.fields
    assert "is_superuser" not in student_page.context["adminform"].form.fields
    assert staff_post.status_code == 403


def test_admin_assigns_roles_in_user_form() -> None:
    client, _admin = login_as("+998902000009", Role.ADMIN)
    user = User.objects.create_user(phone="+998902000010", password="x", first_name="Aziz")

    page = client.get(reverse("admin:users_user_change", args=[user.pk]))
    form = page.context["adminform"].form
    data = {
        name: value
        for name, value in form.initial.items()
        if name in form.fields and value is not None and name not in ("password", "avatar")
    }
    data.update(
        {
            "roles": [Role.TEACHER, Role.MANAGER],
            "is_active": "on",
            "last_login_0": "",
            "last_login_1": "",
            "date_joined_0": "2026-09-28",
            "date_joined_1": "10:00:00",
            "social_accounts-TOTAL_FORMS": 0,
            "social_accounts-INITIAL_FORMS": 0,
        }
    )
    response = client.post(reverse("admin:users_user_change", args=[user.pk]), data)

    assert response.status_code == 302, (
        response.context and response.context["adminform"].form.errors
    )
    user.refresh_from_db()
    assert role_names(user) == {Role.TEACHER, Role.MANAGER}
    assert user.is_staff


@pytest.mark.parametrize(("role", "status"), [(Role.DIRECTOR, 403), (Role.TEACHER, 400)])
def test_video_upload_needs_add_permission(role: str, status: int) -> None:
    client, _user = login_as("+998902000011", role)

    # O'qituvchi yuklay oladi (bo'sh so'rov — 400), direktor faqat ko'radi (403).
    response = client.post("/api/v1/admin/videos/", {}, content_type="application/json")

    assert response.status_code == status
