"""O'qituvchi: navbat, kim nimani ko'radi, qaror va o'quvchiga xabar; admin va statistika."""

from datetime import timedelta
from typing import Any

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.homework.models import Assignment, Submission
from apps.learning.models import Enrollment
from apps.notifications.models import Notification
from apps.stats import metrics
from apps.users.roles import Role

from .conftest import World, api, instructor, make_user

pytestmark = pytest.mark.django_db

QUEUE = "/api/v1/teacher/reviews/"


def submitted(world: World, student: Any = None, **fields: Any) -> Submission:
    return Submission.objects.create(
        assignment=world.assignment, student=student or world.student, text="Tayyor", **fields
    )


def test_group_teacher_sees_queue_and_detail(world: World) -> None:
    submission = submitted(world, code="print(1)", language="python")

    queue = api(world.teacher).get(QUEUE).json()
    detail = api(world.teacher).get(f"{QUEUE}{submission.pk}/").json()

    assert queue["pending"] == 1
    [card] = queue["results"]
    assert card["student_name"] == "Aziz" and card["group_name"] == "FE-1"
    assert card["lesson_title"] == "Dars 0" and card["preview"] == "Tayyor"
    assert detail["submission"]["code"] == "print(1)"
    assert detail["instructions"] == "Kichik sahifa yasang."
    assert detail["next_id"] is None


def test_course_instructor_reviews_students_without_group(world: World) -> None:
    online = make_user("+998901000003", Role.STUDENT)
    Enrollment.objects.create(user=online, course=world.course)
    author = make_user("+998901000004", Role.TEACHER)
    instructor(author, world.course)
    submission = submitted(world, student=online)

    assert api(author).get(f"{QUEUE}{submission.pk}/").status_code == 200
    # Guruh ustozi o'z guruhida bo'lmagan o'quvchining javobini ko'rmaydi.
    assert api(world.teacher).get(f"{QUEUE}{submission.pk}/").status_code == 404


def test_other_teachers_and_students_are_refused(world: World) -> None:
    submission = submitted(world)
    stranger = make_user("+998901000005", Role.TEACHER)

    assert api(stranger).get(f"{QUEUE}{submission.pk}/").status_code == 404
    assert api(stranger).get(QUEUE).json()["results"] == []
    assert api(world.student).get(QUEUE).status_code == 403


def test_accept_needs_score_and_notifies_student(
    world: World, django_capture_on_commit_callbacks: Any
) -> None:
    submission = submitted(world)
    client = api(world.teacher)

    no_score = client.post(f"{QUEUE}{submission.pk}/", {"decision": "accept"}, format="json")
    with django_capture_on_commit_callbacks(execute=True):
        accepted = client.post(
            f"{QUEUE}{submission.pk}/",
            {"decision": "accept", "score": 92, "feedback": "Zo'r!"},
            format="json",
        )
    twice = client.post(
        f"{QUEUE}{submission.pk}/", {"decision": "accept", "score": 50}, format="json"
    )

    assert no_score.status_code == 400
    assert accepted.status_code == 200
    assert accepted.json()["submission"]["status"] == Submission.Status.ACCEPTED
    assert accepted.json()["submission"]["reviewer_name"] == "Ustoz"
    assert twice.status_code == 400
    note = Notification.objects.get(user=world.student)
    assert note.kind == Notification.Kind.HOMEWORK_REVIEWED
    assert "92/100" in note.body and "Zo'r!" in note.body
    assert note.link.endswith(f"/lessons/{world.assignment.lesson_id}#homework")


def test_return_needs_feedback(world: World) -> None:
    submission = submitted(world)
    client = api(world.teacher)

    silent = client.post(f"{QUEUE}{submission.pk}/", {"decision": "return"}, format="json")
    returned = client.post(
        f"{QUEUE}{submission.pk}/",
        {"decision": "return", "feedback": "Rasmni qo'shing"},
        format="json",
    )

    assert silent.status_code == 400
    submission.refresh_from_db()
    assert returned.status_code == 200
    assert submission.status == Submission.Status.CHANGES_REQUESTED and submission.score is None


def test_reviewed_tab_and_group_filter(world: World) -> None:
    submitted(world, status=Submission.Status.ACCEPTED, score=80, reviewed_at=timezone.now())
    client = api(world.teacher)

    reviewed = client.get(QUEUE, {"status": "reviewed"}).json()
    other_group = client.get(QUEUE, {"status": "reviewed", "group": str(world.group.pk + 99)})

    assert [card["score"] for card in reviewed["results"]] == [80]
    assert other_group.json()["results"] == []
    assert reviewed["groups"] == [{"id": world.group.pk, "name": "FE-1"}]


def test_me_counts_pending_reviews(world: World) -> None:
    submitted(world)

    assert api(world.teacher).get("/api/v1/me/").json()["pending_reviews"] == 1
    assert api(world.student).get("/api/v1/me/").json()["pending_reviews"] == 0


def test_group_page_shows_homework(world: World) -> None:
    submitted(world, status=Submission.Status.ACCEPTED, score=90)

    body = api(world.teacher).get(f"/api/v1/teacher/groups/{world.group.pk}/").json()

    [student] = body["students"]
    assert (student["homework_accepted"], student["homework_average"]) == (1, 90)


def test_stale_reviews_are_a_problem(world: World) -> None:
    old = submitted(world)
    Submission.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(hours=49))

    found = {problem.title: problem for problem in metrics.problems(metrics.period("today"))}

    assert found["48 soatdan beri tekshirilmagan uy vazifalari"].count == 1


def test_admin_lists_are_scoped(world: World) -> None:
    submitted(world)
    other = make_user("+998901000006", Role.TEACHER)
    for user, expected in ((world.teacher, 1), (other, 0)):
        client = Client()
        client.force_login(user)
        page = client.get(reverse("admin:homework_submission_changelist"))
        assert page.status_code == 200
        assert len(page.context["cl"].result_list) == expected


def test_teacher_adds_assignment_in_lesson_admin(world: World) -> None:
    instructor(world.teacher, world.course)
    lesson = world.lessons[1]
    client = Client()
    client.force_login(world.teacher)

    page = client.get(reverse("admin:catalog_lesson_change", args=[lesson.pk]))

    assert page.status_code == 200
    models = [inline.formset.model for inline in page.context["inline_admin_formsets"]]
    assert Assignment in models
