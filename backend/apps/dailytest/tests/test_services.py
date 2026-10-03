"""Kunlik test: ochish (07:00), savollar, javoblar va XP, yopish (23:00), eslatma va reyting."""

from datetime import timedelta
from typing import Any

import pytest
from django.core.cache import cache

from apps.catalog.models import Lesson
from apps.dailytest import services
from apps.dailytest.models import DailyAttempt, DailyTest
from apps.live.models import GroupLesson
from apps.notifications.models import Notification
from apps.quizzes.models import Question
from apps.quizzes.services import Layout
from apps.rewards.models import Entry, GameSettings

from .conftest import DAY, World, at, bank, make_user

pytestmark = pytest.mark.django_db


def opened(world: World, day: Any = DAY) -> DailyTest:
    assert services.open_day(now=at(7, day=day)) == 1
    return DailyTest.objects.get(group=world.group, day=day)


def respond(attempt: DailyAttempt, right: int, *, upto: int = 99, now: Any = None) -> None:
    """Birinchi `right` ta savolga to'g'ri, qolganlariga noto'g'ri; `upto` tasigacha."""
    for index, question_id in enumerate(attempt.question_ids[:upto]):
        question = Question.objects.prefetch_related("choices").get(pk=question_id)
        layout = Layout.build(question, attempt.seed)
        target = [choice.is_correct for choice in layout.shown].index(index < right) + 1
        services.answer(attempt, question_id, {"choice": target}, now=now or at(9))


def test_morning_test_from_covered_lessons(world: World) -> None:
    test = opened(world)

    assert (test.status, test.questions_count, test.pool_size) == ("OPEN", 20, 24)
    assert (test.opens_at, test.closes_at) == (at(7), at(23))
    notes = Notification.objects.filter(kind=Notification.Kind.DAILY_TEST)
    assert {note.user for note in notes} == set(world.students)
    note = notes.first()
    assert note is not None and note.title == "📝 Kunlik test ochildi"
    assert note.link == "/dashboard/daily-test" and "20 savol, 23:00 gacha" in note.body
    assert services.open_day(now=at(7, 30)) == 0  # takroriy ishga tushish

    attempt = services.start(test, world.students[0], now=at(8))
    assert len(attempt.question_ids) == len(set(attempt.question_ids)) == 20
    assert not set(attempt.question_ids) & world.hidden  # o'tilmagan dars savoli yo'q
    assert services.start(test, world.students[0], now=at(9)) == attempt


def test_result_counts_and_reward_once(world: World) -> None:
    test = opened(world)
    attempt = services.start(test, world.students[0], now=at(8))
    respond(attempt, right=17)

    result = services.finish(attempt, now=at(9, 30))
    again = services.finish(attempt, now=at(10))

    assert (result.correct, result.wrong, result.xp, result.coins) == (17, 3, 34, 17)
    assert (result.place, result.people) == (1, 1)
    assert again.correct == 17 and attempt.finished_at == at(9, 30)
    entry = Entry.objects.get(user=world.students[0], reason=Entry.Reason.DAILY_TEST)
    assert (entry.xp, entry.coins, entry.note) == (34, 17, "17/20")


def test_answers_are_checked(world: World) -> None:
    test = opened(world)
    attempt = services.start(test, world.students[0], now=at(8))
    first = attempt.question_ids[0]

    with pytest.raises(services.DailyTestError, match="formati"):
        services.answer(attempt, first, {"choice": 9}, now=at(9))
    respond(attempt, right=1, upto=1)
    with pytest.raises(services.DailyTestError, match="javob berilgan"):
        respond(attempt, right=1, upto=1)
    with pytest.raises(services.DailyTestError, match="testda yo'q"):
        services.answer(attempt, min(world.hidden), {"choice": 1}, now=at(9))
    with pytest.raises(services.DailyTestError, match="yopildi"):
        services.answer(attempt, attempt.question_ids[1], {"choice": 1}, now=at(23))


def test_only_group_members_during_the_day(world: World) -> None:
    test = opened(world)
    outsider = make_user("+998901000099", name="Begona")

    with pytest.raises(services.DailyTestError, match="guruhda emassiz"):
        services.start(test, outsider, now=at(8))
    with pytest.raises(services.DailyTestError, match="yopilgan"):
        services.start(test, world.students[1], now=at(23, 1))
    with pytest.raises(services.DailyTestError, match="yopilgan"):
        services.start(test, world.students[1], now=at(6, 59))


def test_answers_open_only_after_closing(world: World) -> None:
    test = opened(world)
    attempt = services.start(test, world.students[0], now=at(8))
    respond(attempt, right=19)
    services.finish(attempt, now=at(9))

    assert not services.can_review(attempt, now=at(22, 59))
    assert services.can_review(attempt, now=at(23))
    review = services.review(attempt)
    assert len(review) == 20 and sum(item["correct"] for item in review) == 19
    assert all(item["correct_answer"] for item in review)


def test_closing_counts_unfinished_attempts(world: World) -> None:
    test = opened(world)
    attempt = services.start(test, world.students[0], now=at(8))
    respond(attempt, right=5, upto=5)

    assert services.close_day(now=at(22)) == 0
    assert services.close_day(now=at(23, 5)) == 1

    test.refresh_from_db()
    attempt.refresh_from_db()
    assert test.status == DailyTest.Status.CLOSED
    assert (attempt.correct, attempt.total, attempt.finished_at) == (5, 20, at(23))
    assert Entry.objects.get(reason=Entry.Reason.DAILY_TEST).xp == 10


def test_yesterday_questions_are_avoided(world: World) -> None:
    extra = Lesson.objects.create(module=world.lessons[0].module, title_uz="Dars 4", order=4)
    bank(extra, 24)  # o'tilgan darslarda jami 48 savol
    GroupLesson.objects.create(group=world.group, lesson=extra, opened_by=world.teacher)
    first = services.start(opened(world), world.students[0], now=at(8))
    tomorrow = DAY + timedelta(days=1)

    second = services.start(opened(world, tomorrow), world.students[0], now=at(8, day=tomorrow))

    assert not set(first.question_ids) & set(second.question_ids)


def test_too_few_questions_skip_the_test_and_warn_the_teacher(world: World) -> None:
    GroupLesson.objects.filter(lesson=world.lessons[1]).delete()  # bankda 12 ta qoldi

    assert services.open_day(now=at(7)) == 0
    assert services.open_day(now=at(7, day=DAY + timedelta(days=1))) == 0

    assert set(DailyTest.objects.values_list("status", flat=True)) == {"SKIPPED"}
    assert not Notification.objects.filter(kind=Notification.Kind.DAILY_TEST).exists()
    [warning] = Notification.objects.filter(kind=Notification.Kind.DAILY_TEST_TEACHER)
    assert warning.user == world.teacher and "Python-1" in warning.title
    assert "12 ta savol bor, kamida 20 ta kerak" in warning.body


def test_can_be_switched_off(world: World) -> None:
    GameSettings.objects.update_or_create(pk=1, defaults={"daily_test": False})
    cache.clear()

    assert services.open_day(now=at(7)) == 0
    assert not DailyTest.objects.exists()


def test_reminder_goes_to_those_who_did_not_finish(world: World) -> None:
    test = opened(world)
    done, started, idle = world.students
    finished = services.start(test, done, now=at(8))
    respond(finished, right=20)
    services.finish(finished, now=at(9))
    services.start(test, started, now=at(10))

    assert services.remind(now=at(20)) == 2
    assert services.remind(now=at(20, 5)) == 0
    reminded = Notification.objects.filter(title="⏳ Kunlik test 23:00 da yopiladi")
    assert {note.user for note in reminded} == {started, idle}


def test_day_and_week_ratings(world: World) -> None:
    ali, bekzod, dilnoza = world.students
    monday = opened(world)
    for student, right, minute in ((bekzod, 18, 30), (ali, 18, 10), (dilnoza, 10, 20)):
        attempt = services.start(monday, student, now=at(8))
        respond(attempt, right=right)
        services.finish(attempt, now=at(9, minute))
    tuesday = DAY + timedelta(days=1)
    attempt = services.start(opened(world, tuesday), dilnoza, now=at(8, day=tuesday))
    respond(attempt, right=20, now=at(9, day=tuesday))
    services.finish(attempt, now=at(9, day=tuesday))

    day = services.day_rating(monday)
    week = services.week_rating(world.group, tuesday)

    # Teng natijada — kim oldin tugatgan.
    assert [(row.name, row.correct) for row in day] == [
        ("Ali V.", 18),
        ("Bekzod K.", 18),
        ("Dilnoza S.", 10),
    ]
    assert [(row.name, row.correct, row.total) for row in week] == [
        ("Dilnoza S.", 30, 40),
        ("Ali V.", 18, 20),
        ("Bekzod K.", 18, 20),
    ]


def test_morning_message_tells_yesterdays_result(world: World) -> None:
    attempt = services.start(opened(world), world.students[0], now=at(8))
    respond(attempt, right=17)
    services.finish(attempt, now=at(9))

    opened(world, DAY + timedelta(days=1))

    note = Notification.objects.filter(user=world.students[0]).latest("pk")
    assert "Kecha: 17/20, guruhda 1-o'rin (1 kishidan)." in note.body
