"""Kunlik test saytda: o'quvchi ko'rinishi, javoblar (test yopilgach) va o'qituvchi jadvali."""

from typing import Any
from unittest import mock

import pytest
from django.utils import timezone

from apps.dailytest import services
from apps.dailytest.models import DailyAttempt, DailyTest
from apps.quizzes.models import Question
from apps.quizzes.services import Layout
from apps.users.roles import Role

from .conftest import DAY, World, api, at, make_user
from .test_services import opened, respond

pytestmark = pytest.mark.django_db


def frozen(moment: Any) -> Any:
    return mock.patch.object(timezone, "now", return_value=moment)


def finished(test: DailyTest, world: World, index: int, right: int, minute: int) -> DailyAttempt:
    attempt = services.start(test, world.students[index], now=at(8))
    respond(attempt, right=right)
    services.finish(attempt, now=at(9, minute))
    return attempt


def test_student_overview(world: World, settings: Any) -> None:
    settings.TELEGRAM_BOT_USERNAME = "sifat_test_bot"
    test = opened(world)
    mine = finished(test, world, 0, right=15, minute=30)
    finished(test, world, 1, right=18, minute=10)

    with frozen(at(12)):
        data = api(world.students[0]).get("/api/v1/daily-test/").json()

    assert data["enabled"] is True and data["bot_url"] == "https://t.me/sifat_test_bot?start=dt"
    [group] = data["groups"]
    assert (group["name"], group["course"]) == ("Python-1", "Python")
    today = group["today"]
    assert (today["id"], today["questions_count"], today["open"]) == (test.pk, 20, True)
    assert today["attempt"] == {
        "id": mine.pk,
        "correct": 15,
        "total": 20,
        "finished": True,
        "reviewable": False,
    }
    assert group["day_rating"] == [
        {"name": "Bekzod K.", "correct": 18, "total": 20, "me": False},
        {"name": "Ali V.", "correct": 15, "total": 20, "me": True},
    ]
    assert [row["name"] for row in group["week_rating"]] == ["Bekzod K.", "Ali V."]
    assert group["history"] == [
        {"attempt_id": mine.pk, "day": str(DAY), "correct": 15, "total": 20, "reviewable": False}
    ]


def test_review_only_own_attempt_after_closing(world: World) -> None:
    test = opened(world)
    mine = finished(test, world, 0, right=19, minute=0)
    url = f"/api/v1/daily-test/attempts/{mine.pk}/"

    with frozen(at(22)):
        early = api(world.students[0]).get(url)
    with frozen(at(23, 1)):
        late = api(world.students[0]).get(url)
        stranger = api(world.students[1]).get(url)

    assert early.status_code == 403 and "23:00 dan keyin" in early.json()["error"]["message"]
    assert late.status_code == 200
    body = late.json()
    assert (body["correct"], body["total"], body["group"]) == (19, 20, "Python-1")
    assert len(body["review"]) == len(body["review_questions"]) == 20
    assert sum(item["correct"] for item in body["review"]) == 19
    assert all(item["correct_answer"] and item["explanation"] == "" for item in body["review"])
    assert stranger.status_code == 404


def test_teacher_sees_who_did_not_do_it(world: World) -> None:
    test = opened(world)
    finished(test, world, 0, right=17, minute=0)
    services.start(test, world.students[1], now=at(10))
    url = f"/api/v1/teacher/groups/{world.group.pk}/daily-test/?day={DAY}"

    data = api(world.teacher).get(url).json()

    assert (data["status"], data["questions_count"], data["pool_size"], data["done"]) == (
        "OPEN",
        20,
        24,
        1,
    )
    assert [(row["name"], row["status"], row["correct"]) for row in data["students"]] == [
        ("Dilnoza Saidova", "NONE", None),
        ("Bekzod Karimov", "STARTED", None),
        ("Ali Valiyev", "DONE", 17),
    ]
    assert data["recent"] == [{"day": str(DAY), "status": "OPEN", "done": 1}]


def test_teacher_view_is_limited_to_own_groups(world: World) -> None:
    other = make_user("+998901000077", Role.TEACHER, name="Boshqa")
    url = f"/api/v1/teacher/groups/{world.group.pk}/daily-test/"

    assert api(other).get(url).status_code == 404
    assert api(world.students[0]).get(url).status_code == 403
    empty = api(world.teacher).get(url).json()
    assert (empty["status"], empty["pool_size"], empty["done"]) == ("NONE", 24, 0)
    assert [row["status"] for row in empty["students"]] == ["NONE", "NONE", "NONE"]


def problem(response: Any) -> str:
    """Frontend o'qiydigan xato matni (`non_field_errors`)."""
    return str(response.json()["error"]["fields"]["non_field_errors"][0])


def right_position(attempt: DailyAttempt, question_id: int) -> int:
    question = Question.objects.prefetch_related("choices").get(pk=question_id)
    layout = Layout.build(question, attempt.seed)
    return [choice.is_correct for choice in layout.shown].index(True) + 1


def test_daily_test_on_the_site(world: World) -> None:
    test = opened(world)
    client = api(world.students[0])
    start = f"/api/v1/daily-test/{test.pk}/start/"

    with frozen(at(9)):
        started = client.post(start).json()
    attempt = DailyAttempt.objects.get(pk=started["id"])
    first = started["questions"][0]["id"]
    position = right_position(attempt, first)
    answer_url = f"/api/v1/daily-test/attempts/{attempt.pk}/answers/"
    body = {"question": first, "response": {"choice": position}}
    with frozen(at(9, 5)):
        saved = client.post(answer_url, body, format="json")
        again = client.post(answer_url, body, format="json")
        resumed = client.post(start).json()

    assert (started["total"], started["finished"], started["answers"]) == (20, False, [])
    assert started["seconds_left"] == 14 * 3600  # 09:00 → 23:00
    # Javobdan keyin baho yo'q — natija oxirida (soni), javoblar 23:00 dan keyin.
    assert saved.status_code == 200 and saved.json() == body
    assert again.status_code == 400 and "javob berilgan" in problem(again)
    assert resumed["id"] == attempt.pk and resumed["answers"] == [body]

    for index, question_id in enumerate(attempt.question_ids[1:]):
        good = right_position(attempt, question_id)
        services.answer(
            attempt, question_id, {"choice": good if index < 16 else 3 - good}, now=at(9, 30)
        )
    with frozen(at(10)):
        result = client.post(f"/api/v1/daily-test/attempts/{attempt.pk}/finish/").json()

    assert result == {
        "correct": 17,
        "wrong": 3,
        "total": 20,
        "xp": 34,
        "coins": 17,
        "place": 1,
        "people": 1,
    }


def test_site_test_access_rules(world: World) -> None:
    test = opened(world)
    outsider = make_user("+998901000088", name="Begona")
    mine = services.start(test, world.students[0], now=at(8))

    with frozen(at(9)):
        stranger = api(outsider).post(f"/api/v1/daily-test/{test.pk}/start/")
        foreign = api(world.students[1]).post(
            f"/api/v1/daily-test/attempts/{mine.pk}/answers/",
            {"question": mine.question_ids[0], "response": {"choice": 1}},
            format="json",
        )
    with frozen(at(23, 5)):
        late = api(world.students[2]).post(f"/api/v1/daily-test/{test.pk}/start/")

    assert stranger.status_code == 404
    assert foreign.status_code == 404
    assert late.status_code == 400 and "yopilgan" in problem(late)
