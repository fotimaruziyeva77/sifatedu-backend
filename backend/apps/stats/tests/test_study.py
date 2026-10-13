"""Admin bosh sahifasidagi «O'quv jarayoni» (bugungi darslar, guruhlar, imtihonlar) va
muammolardan saytdagi kerakli sahifaga havolalar."""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Category, Course, Lesson, Module
from apps.dailytest.models import DailyAttempt, DailyTest
from apps.exams.models import Exam, ExamAttempt, ExamTask, TaskAnswer
from apps.exams.services import month_start
from apps.homework.models import Assignment, Submission
from apps.learning.models import Enrollment, StudyGroup
from apps.live.models import Attendance, LiveLesson
from apps.stats import metrics, study
from apps.users.models import User
from apps.users.roles import Role, set_roles

pytestmark = pytest.mark.django_db


def person(phone: str, *roles: str, name: str = "Aziz") -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name=name)
    if roles:
        set_roles(user, roles)
    return user


@dataclass
class School:
    lesson: Lesson
    group: StudyGroup
    students: list[User]
    exam: Exam
    task: ExamTask
    admin: User


@pytest.fixture
def school(db: Any) -> School:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="python", title_uz="Python", category=category)
    module = Module.objects.create(course=course, title_uz="Asoslar")
    lesson = Lesson.objects.create(module=module, title_uz="O'zgaruvchilar", order=1)
    teacher = person("+998903000001", Role.TEACHER, name="Ustoz")
    group = StudyGroup.objects.create(
        course=course, teacher=teacher, name="Python-1", status=StudyGroup.Status.ACTIVE
    )
    StudyGroup.objects.create(
        course=course, teacher=teacher, name="Eski", status=StudyGroup.Status.FINISHED
    )
    students = [person(f"+99890100000{index}", Role.STUDENT) for index in (1, 2)]
    for student in students:
        Enrollment.objects.create(user=student, course=course, group=group)
    now = timezone.now()
    exam = Exam.objects.create(
        course=course,
        month=month_start(timezone.localdate()),
        status=Exam.Status.READY,
        opens_at=now - timedelta(hours=1),
        closes_at=now + timedelta(days=2),
    )
    task = ExamTask.objects.create(exam=exam, order=1, title="Kalkulyator", instructions="Yozing")
    return School(lesson, group, students, exam, task, person("+998909000001", Role.ADMIN))


def at(hour: int, minute: int = 0) -> datetime:
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hour, minute)))


def mark(lesson: LiveLesson, student: User, status: str) -> None:
    Attendance.objects.create(
        live_lesson=lesson,
        student=student,
        status=status,
        marked_by=lesson.group.teacher,
        marked_at=lesson.ends_at,
    )


def test_lessons_today_show_attendance_state(school: School) -> None:
    group = school.group
    marked = LiveLesson.objects.create(group=group, starts_at=at(9), duration_min=60)
    mark(marked, school.students[0], Attendance.Status.PRESENT)
    mark(marked, school.students[1], Attendance.Status.ABSENT)
    unmarked = LiveLesson.objects.create(group=group, starts_at=at(10), duration_min=60)
    # "Qo'shilish" bilan yozilgani — o'qituvchi belgilagan davomat emas.
    Attendance.objects.create(
        live_lesson=unmarked, student=school.students[0], status=Attendance.Status.PRESENT
    )
    live = LiveLesson.objects.create(group=group, starts_at=at(11, 30), duration_min=60)
    later = LiveLesson.objects.create(group=group, starts_at=at(18), duration_min=90)
    canceled = LiveLesson.objects.create(
        group=group, starts_at=at(16), duration_min=90, canceled_at=at(8)
    )
    LiveLesson.objects.create(group=group, starts_at=at(9) - timedelta(days=1), duration_min=60)

    rows = study.lessons_today(school.admin, now=at(12))

    assert [row.lesson for row in rows] == [marked, unmarked, live, canceled, later]
    states = {row.lesson.pk: row.state for row in rows}
    assert states == {
        marked.pk: "marked",
        unmarked.pk: "unmarked",
        live.pk: "live",
        canceled.pk: "canceled",
        later.pk: "upcoming",
    }
    assert (rows[0].came, rows[0].late, rows[0].absent) == (1, 0, 1)
    assert rows[0].url == f"/uz/dashboard/teaching/live/{marked.pk}"
    # Direktor kabinetga kirmaydi — havola yo'q.
    director = person("+998909000002", Role.DIRECTOR)
    assert study.lessons_today(director, now=at(12))[0].url == ""


def test_groups_overview_counts_attendance_daily_test_and_unchecked_work(school: School) -> None:
    first, second = school.students
    lesson = LiveLesson.objects.create(group=school.group, starts_at=at(9), duration_min=60)
    mark(lesson, first, Attendance.Status.LATE)
    mark(lesson, second, Attendance.Status.ABSENT)
    test = DailyTest.objects.create(
        group=school.group, day=timezone.localdate(), opens_at=at(7), closes_at=at(23)
    )
    DailyAttempt.objects.create(test=test, student=first, finished_at=at(8))
    DailyAttempt.objects.create(test=test, student=second)  # boshlagan, tugatmagan
    assignment = Assignment.objects.create(lesson=school.lesson, instructions="Yozing")
    Submission.objects.create(assignment=assignment, student=first, text="Tayyor")
    TaskAnswer.objects.create(task=school.task, student=second, text="Mana")

    rows = study.groups_overview(school.admin, now=at(12))

    assert [row.group.name for row in rows] == ["Python-1"]
    row = rows[0]
    assert (row.students, row.attendance, row.daily_done, row.unchecked) == (2, 50, 1, 2)
    assert row.url == f"/uz/dashboard/teaching/{school.group.pk}"
    DailyTest.objects.all().delete()
    assert study.groups_overview(school.admin, now=at(12))[0].daily_done is None


def test_exams_overview_shows_progress_and_grading_link(school: School) -> None:
    first, second = school.students
    ExamAttempt.objects.create(
        exam=school.exam, student=first, deadline=timezone.now(), finished_at=timezone.now()
    )
    TaskAnswer.objects.create(task=school.task, student=second, text="Mana")
    closed = Exam.objects.create(
        course=school.exam.course,
        month=month_start(timezone.localdate() - timedelta(days=62)),
        status=Exam.Status.READY,
        opens_at=timezone.now() - timedelta(days=60),
        closes_at=timezone.now() - timedelta(days=55),
    )

    rows = study.exams_overview(school.admin)

    assert [row.exam for row in rows] == [school.exam]
    row = rows[0]
    assert (row.state, row.students, row.tested, row.to_grade) == ("open", 2, 1, 1)
    assert row.url == f"/uz/dashboard/teaching/exams/{school.exam.pk}"
    # Eski imtihon baholanmagan javob bilan qaytadi va alohida muddat bilan "ochiq" ko'rinadi.
    old_task = ExamTask.objects.create(exam=closed, order=1, title="Eski", instructions="-")
    TaskAnswer.objects.create(task=old_task, student=first, text="Kech")
    closed.extensions.create(student=first, until=timezone.now() + timedelta(hours=3))
    states = {row.exam.pk: row.state for row in study.exams_overview(school.admin)}
    assert states == {school.exam.pk: "open", closed.pk: "extended"}


def test_problems_lead_to_the_site_pages(school: School) -> None:
    now = timezone.now()
    answer = TaskAnswer.objects.create(task=school.task, student=school.students[1], text="Mana")
    TaskAnswer.objects.filter(pk=answer.pk).update(updated_at=now - timedelta(days=3))
    assignment = Assignment.objects.create(lesson=school.lesson, instructions="Yozing")
    submission = Submission.objects.create(
        assignment=assignment, student=school.students[0], text="Tayyor"
    )
    Submission.objects.filter(pk=submission.pk).update(created_at=now - timedelta(days=3))
    unmarked = LiveLesson.objects.create(
        group=school.group, starts_at=now - timedelta(days=1), duration_min=90
    )
    # Hali 2 soat o'tmagan va o'quvchisiz guruhdagi darslar — muammo emas.
    LiveLesson.objects.create(
        group=school.group, starts_at=now - timedelta(minutes=150), duration_min=90
    )
    empty = StudyGroup.objects.create(
        course=school.group.course, teacher=school.group.teacher, name="Bo'sh"
    )
    LiveLesson.objects.create(group=empty, starts_at=now - timedelta(days=1), duration_min=90)
    titles = (
        "Baholanmagan imtihon topshiriqlari",
        "48 soatdan beri tekshirilmagan uy vazifalari",
        "Yo'qlama qilinmagan darslar",
    )

    def links(viewer: User) -> dict[str, tuple[int, str]]:
        found = metrics.problems(metrics.period("today"), viewer)
        return {item.title: (item.count, item.url) for item in found if item.title in titles}

    assert links(school.admin) == {
        titles[0]: (1, f"/uz/dashboard/teaching/exams/{school.exam.pk}"),
        titles[1]: (1, "/uz/dashboard/reviews"),
        titles[2]: (1, f"/uz/dashboard/teaching/live/{unmarked.pk}"),
    }
    # Menejer uy vazifasini tekshirmaydi — admin ro'yxatiga; direktor kabinetga kirmaydi.
    manager = links(person("+998909000003", Role.MANAGER))
    assert manager[titles[1]][1] == "/admin/homework/submission/?status__exact=SUBMITTED"
    assert manager[titles[2]][1] == f"/uz/dashboard/teaching/live/{unmarked.pk}"
    director = links(person("+998909000004", Role.DIRECTOR))
    assert director[titles[2]][1] == "/admin/live/livelesson/"
    assert director[titles[0]][1] == f"/uz/dashboard/teaching/exams/{school.exam.pk}"


def test_dashboard_page_shows_the_learning_section(school: School) -> None:
    LiveLesson.objects.create(
        group=school.group, starts_at=timezone.now() + timedelta(minutes=30), duration_min=90
    )
    client = Client()
    client.force_login(school.admin)

    html = client.get(reverse("admin:index")).content.decode()

    assert "O'quv jarayoni" in html and "Bugungi darslar" in html
    assert f'href="/uz/dashboard/teaching/{school.group.pk}"' in html
    assert f'href="/uz/dashboard/teaching/exams/{school.exam.pk}"' in html
    assert 'href="/uz/dashboard/teaching"' in html
