"""Admin menyusi: muhim bo'limlar yonidagi sonlar va saytdagi guruhlar kabinetiga havola."""

from datetime import timedelta
from typing import Any

import pytest
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Category, Course, Lesson, Module
from apps.core import admin_config
from apps.exams.models import Exam, ExamTask, TaskAnswer
from apps.exams.services import month_start
from apps.homework.models import Assignment, Submission
from apps.learning.models import Enrollment, StudyGroup
from apps.payments.models import Order, Refund
from apps.shop.models import Product, Purchase
from apps.users.models import User
from apps.users.roles import Role, set_roles

pytestmark = pytest.mark.django_db


def person(phone: str, *roles: str) -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name="Xodim")
    set_roles(user, roles)
    return user


def request_for(user: User) -> Any:
    request = RequestFactory().get("/admin/")
    request.user = user
    return request


@pytest.fixture
def course(db: Any) -> Course:
    category = Category.objects.create(slug="it", name_uz="IT")
    return Course.objects.create(slug="python", title_uz="Python", category=category)


def test_badges_count_what_waits_for_this_person(course: Course) -> None:
    teacher, other = person("+998903000001", Role.TEACHER), person("+998903000002", Role.TEACHER)
    mine, theirs = (
        StudyGroup.objects.create(course=course, teacher=teacher, name="Mine"),
        StudyGroup.objects.create(course=course, teacher=other, name="Theirs"),
    )
    students = [person(f"+99890100000{index}", Role.STUDENT) for index in (1, 2)]
    Enrollment.objects.create(user=students[0], course=course, group=mine)
    Enrollment.objects.create(user=students[1], course=course, group=theirs)
    lesson = Lesson.objects.create(module=Module.objects.create(course=course, title_uz="M"))
    assignment = Assignment.objects.create(lesson=lesson, instructions="Yozing")
    now = timezone.now()
    exam = Exam.objects.create(
        course=course,
        month=month_start(timezone.localdate()),
        status=Exam.Status.READY,
        opens_at=now,
        closes_at=now + timedelta(days=1),
    )
    task = ExamTask.objects.create(exam=exam, order=1, title="T", instructions="-")
    for student in students:
        Submission.objects.create(assignment=assignment, student=student, text="Tayyor")
        TaskAnswer.objects.create(task=task, student=student, text="Mana")
    order = Order.objects.create(user=students[0], course=course, amount=100_000)
    Refund.objects.create(order=order, amount=order.amount, reason="Sinov")
    product = Product.objects.create(name_uz="Daftar", price=10)
    Purchase.objects.create(product=product, user=students[0], name="Daftar", price=10)
    admin = person("+998909000001", Role.ADMIN)

    def badges(user: User) -> list[str | None]:
        request = request_for(user)
        return [
            admin_config.homework_badge(request),
            admin_config.exam_grading_badge(request),
            admin_config.refunds_badge(request),
            admin_config.shop_badge(request),
        ]

    assert badges(admin) == ["2", "2", "1", "1"]
    # O'qituvchi — faqat o'z guruhi o'quvchilariniki.
    assert badges(teacher)[:2] == ["1", "1"]
    TaskAnswer.objects.update(score=80)
    assert admin_config.exam_grading_badge(request_for(admin)) is None


def test_cabinet_link_opens_the_site_for_group_managers(db: Any) -> None:
    admin = person("+998909000001", Role.ADMIN)
    director = person("+998909000002", Role.DIRECTOR)
    client = Client()
    client.force_login(admin)

    html = client.get(reverse("admin:index")).content.decode()

    assert 'href="/uz/dashboard/teaching"' in html and "Kabinet: guruhlar" in html
    assert admin_config.cabinet_permission(request_for(admin))
    assert not admin_config.cabinet_permission(request_for(director))
    assert admin_config.cabinet_permission(request_for(person("+998903000009", Role.TEACHER)))
