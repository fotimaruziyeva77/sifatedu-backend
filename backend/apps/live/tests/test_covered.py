"""Offlayn guruh: test va uy vazifasi ustoz "Dars o'tildi" deb belgilagach ochiladi."""

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Course, Lesson, Module
from apps.homework.models import Assignment
from apps.learning.models import StudyGroup
from apps.live.models import GroupLesson, LiveLesson
from apps.notifications.models import Notification
from apps.quizzes.models import Choice, Question, Quiz
from apps.users.models import User
from apps.users.roles import Role

from .conftest import World, api, live, make_user, soon

pytestmark = pytest.mark.django_db


@pytest.fixture
def offline(world: World) -> World:
    StudyGroup.objects.filter(pk=world.group.pk).update(study_format="OFFLINE")
    world.group.refresh_from_db()
    for lesson in world.lessons:
        Assignment.objects.create(lesson=lesson, title=f"Vazifa {lesson.pk}", instructions="Yozing")
        quiz = Quiz.objects.create(lesson=lesson)
        question = Question.objects.create(quiz=quiz, text="HTML nima?")
        Choice.objects.create(question=question, text="Til", is_correct=True)
        Choice.objects.create(question=question, text="Rang")
    return world


def lesson_page(user: User, lesson: Lesson) -> dict[str, Any]:
    body: dict[str, Any] = api(user).get(f"/api/v1/lessons/{lesson.pk}/").json()
    return body


def cover(user: User, lesson: LiveLesson, topic: Lesson) -> Any:
    return api(user).post(
        f"/api/v1/teacher/live/{lesson.pk}/covered/", {"lesson": topic.pk}, format="json"
    )


def opened() -> list[Notification]:
    return list(Notification.objects.filter(kind=Notification.Kind.LESSON_OPENED))


def test_tasks_wait_for_the_teacher_in_offline_groups(offline: World) -> None:
    first = offline.lessons[0]
    quiz = Quiz.objects.get(lesson=first)
    assignment = Assignment.objects.get(lesson=first)

    page = lesson_page(offline.student, first)
    start = api(offline.student).post(f"/api/v1/quizzes/{quiz.pk}/attempts/")
    submit = api(offline.student).post(
        f"/api/v1/homework/{assignment.pk}/submissions/", {"text": "Tayyor"}, format="multipart"
    )
    todo = api(offline.student).get("/api/v1/homework/").json()

    assert (page["tasks_locked"], page["homework"], page["quiz"]) == (True, None, None)
    assert start.status_code == 403 and "ustoz darsni o'tgach" in str(start.json())
    assert submit.status_code == 403
    assert todo == []
    # Video va dars sahifasi o'zi ochiq qoladi.
    assert page["id"] == first.pk


def test_marking_a_lesson_opens_it_and_all_before_it(offline: World) -> None:
    first, second = offline.lessons
    session = live(offline, soon(-30))

    response = cover(offline.teacher, session, second)

    assert response.status_code == 200, response.json()
    body = response.json()
    assert (body["topic_id"], body["covered"], body["can_uncover"]) == (second.pk, True, True)
    assert [row["covered"] for row in body["course_lessons"]] == [False, True]
    for lesson in (first, second):
        page = lesson_page(offline.student, lesson)
        assert page["tasks_locked"] is False and page["quiz"] is not None
    assert {note.user for note in opened()} == {offline.student, offline.classmate}
    note = next(note for note in opened() if note.user == offline.student)
    assert note.title == "Yangi dars ochildi: Dars 2"
    assert note.link == f"/dashboard/courses/frontend/lessons/{second.pk}"
    # Qayta bosilsa — xabar takrorlanmaydi.
    cover(offline.teacher, session, second)
    assert len(opened()) == 2


def test_marking_rules(offline: World) -> None:
    started = live(offline, soon(-30))
    future = live(offline, soon(120))
    canceled = live(offline, soon(-60), canceled_at=timezone.now())
    backend = Course.objects.create(
        slug="backend", title_uz="Backend", category=offline.course.category
    )
    foreign = Lesson.objects.create(
        module=Module.objects.create(course=backend, title_uz="Python"), title_uz="Python"
    )
    stranger = make_user("+998901000011", Role.TEACHER)

    assert cover(offline.teacher, started, foreign).status_code == 400
    assert cover(offline.teacher, future, offline.lessons[0]).status_code == 400
    assert cover(offline.teacher, canceled, offline.lessons[0]).status_code == 400
    assert cover(stranger, started, offline.lessons[0]).status_code == 404
    assert not GroupLesson.objects.exists()


def test_undo_closes_the_lesson_again(offline: World) -> None:
    session = live(offline, soon(-30))
    cover(offline.teacher, session, offline.lessons[1])

    response = api(offline.teacher).delete(f"/api/v1/teacher/live/{session.pk}/covered/")

    assert response.status_code == 200
    assert (response.json()["covered"], response.json()["can_uncover"]) == (False, False)
    assert lesson_page(offline.student, offline.lessons[0])["tasks_locked"] is True


def test_online_groups_are_not_gated(world: World) -> None:
    Assignment.objects.create(lesson=world.lessons[0], title="Vazifa", instructions="Yozing")

    page = lesson_page(world.student, world.lessons[0])

    assert page["tasks_locked"] is False and page["homework"] is not None


def test_manager_marks_lessons_in_group_admin(offline: World) -> None:
    admin = User.objects.create_superuser(phone="+998900000009", password="x")
    client = Client()
    client.force_login(admin)
    url = reverse("admin:learning_studygroup_change", args=[offline.group.pk])
    form: dict[str, Any] = {
        "name": offline.group.name,
        "course": offline.course.pk,
        "teacher": offline.teacher.pk,
        "study_format": "OFFLINE",
        "schedule": "",
        "starts_on": "",
        "meet_url": "",
        "room": "3-xona",
        "capacity": "",
        "status": "ACTIVE",
        "students": list(offline.group.enrollments.values_list("pk", flat=True)),
        "slots-TOTAL_FORMS": "0",
        "slots-INITIAL_FORMS": "0",
        "slots-MIN_NUM_FORMS": "0",
        "slots-MAX_NUM_FORMS": "1000",
        "covered_lessons-TOTAL_FORMS": "1",
        "covered_lessons-INITIAL_FORMS": "0",
        "covered_lessons-MIN_NUM_FORMS": "0",
        "covered_lessons-MAX_NUM_FORMS": "1000",
        "covered_lessons-0-lesson": offline.lessons[0].pk,
    }

    response = client.post(url, form)

    assert response.status_code == 302, response.content.decode()[:3000]
    record = GroupLesson.objects.get()
    assert (record.lesson, record.opened_by) == (offline.lessons[0], admin)
    assert len(opened()) == 2
