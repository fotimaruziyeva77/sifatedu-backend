"""O'quvchi: test boshlash (javobsiz), davom ettirish, javob berish, yakunlash va natijalar."""

import json
from collections.abc import Callable, Collection
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.learning.models import LessonProgress
from apps.quizzes import services
from apps.quizzes.models import Answer, Attempt, Question, Quiz
from apps.users.models import User
from apps.users.roles import Role

from .conftest import KINDS, STEPS, World, api, make_user, right_answer, wrong_answer

pytestmark = pytest.mark.django_db


def start(world: World, *, new: bool = False, user: User | None = None) -> Any:
    suffix = "?new=true" if new else ""
    return api(user or world.student).post(f"/api/v1/quizzes/{world.quiz.pk}/attempts/{suffix}")


def reply(
    world: World,
    attempt: dict[str, Any],
    question: dict[str, Any],
    response: Any,
    *,
    user: User | None = None,
) -> Any:
    return api(user or world.student).post(
        f"/api/v1/quiz-attempts/{attempt['id']}/answers/",
        {"question": question["id"], "response": response},
        format="json",
    )


def finish(world: World, attempt: dict[str, Any], *, user: User | None = None) -> Any:
    return api(user or world.student).post(f"/api/v1/quiz-attempts/{attempt['id']}/finish/")


def play(world: World, wrong: Collection[str] = ()) -> dict[str, Any]:
    """Testni boshidan oxirigacha: `wrong` dagi turlarga ataylab xato javob."""
    attempt = start(world, new=True).json()
    for question in attempt["questions"]:
        answer = wrong_answer if question["kind"] in wrong else right_answer
        assert reply(world, attempt, question, answer(question)).status_code == 200
    result: dict[str, Any] = finish(world, attempt).json()
    return result


def lesson_quiz(world: World) -> Any:
    return api(world.student).get(f"/api/v1/lessons/{world.quiz.lesson_id}/").json()["quiz"]


def shown_answer(question: dict[str, Any]) -> dict[str, Any]:
    """To'g'ri javob API da qanday ko'rinishda qaytadi."""
    expected = right_answer(question)
    if question["kind"] == "SINGLE":
        return {"choices": [expected["choice"]]}
    if question["kind"] == "TEXT":
        return {"text": "h1"}
    return expected


def test_start_serves_questions_without_answers(world: World) -> None:
    response = start(world)

    assert response.status_code == 200
    body = response.json()
    assert (body["title"], body["total"], body["pass_percent"]) == ("HTML asoslari", 5, 70)
    assert [question["kind"] for question in body["questions"]] == KINDS
    assert body["answers"] == []
    raw = json.dumps(body, ensure_ascii=False)
    for secret in ("is_correct", "<h1>", "belgilash tili", "match"):
        assert secret not in raw
    # Variant ID — ekrandagi o'rni: baza ID lari (yaratilish tartibi) ko'rinmaydi.
    for question in body["questions"]:
        for key in ("options", "items", "left", "right"):
            assert [item["id"] for item in question[key]] == list(range(1, len(question[key]) + 1))
    match = body["questions"][4]
    assert [item["text"] for item in match["left"]] == ["HTML", "CSS", "JavaScript"]
    assert {item["text"] for item in match["right"]} == {"tuzilma", "ko'rinish", "harakat"}


def test_layout_is_stable_per_attempt_and_hides_order(world: World) -> None:
    order, match = world.quiz.questions.filter(kind__in=["ORDER", "MATCH"]).order_by("order")
    orders, rights = set(), set()

    for seed in range(1, 40):
        items = tuple(
            item["text"] for item in services.Layout.build(order, seed).payload()["items"]
        )
        right = services.Layout.build(match, seed).payload()["right"]
        orders.add(items)
        rights.add(tuple(item["text"] for item in right))
        # Tartiblash hech qachon tayyor (to'g'ri) holda berilmaydi.
        assert list(items) != STEPS

    assert len(orders) > 1 and len(rights) > 1
    assert services.Layout.build(match, 7).payload() == services.Layout.build(match, 7).payload()


def test_unfinished_attempt_is_resumed(world: World) -> None:
    first = start(world).json()
    question = first["questions"][0]
    reply(world, first, question, right_answer(question))

    again = start(world).json()
    fresh = start(world, new=True).json()

    assert again["id"] == first["id"]
    assert again["questions"] == first["questions"]
    [done] = again["answers"]
    assert (done["question"], done["correct"]) == (question["id"], True)
    assert done["response"] == right_answer(question)
    assert fresh["id"] != first["id"] and fresh["answers"] == []
    # Bir kundan eski tugallanmagan urinish davom ettirilmaydi.
    Attempt.objects.update(started_at=timezone.now() - timedelta(hours=25))
    assert start(world).json()["id"] not in (first["id"], fresh["id"])


@pytest.mark.parametrize("kind", KINDS)
def test_each_kind_is_graded(world: World, kind: str) -> None:
    results = []
    for answer in (right_answer, wrong_answer):
        attempt = start(world, new=True).json()
        question = next(item for item in attempt["questions"] if item["kind"] == kind)
        response = reply(world, attempt, question, answer(question))
        assert response.status_code == 200, response.json()
        results.append(response.json())
    right, wrong = results

    assert right["correct"] is True and wrong["correct"] is False
    # Test davomida faqat to'g'ri/noto'g'ri: to'g'ri javob va izoh test o'tilgach.
    assert wrong["response"] == wrong_answer(question)
    assert (wrong["correct_answer"], wrong["explanation"]) == (None, "")


def test_answers_are_revealed_only_after_passing(world: World) -> None:
    attempt = start(world).json()
    for question in attempt["questions"]:
        answer = wrong_answer if question["kind"] == "SINGLE" else right_answer
        reply(world, attempt, question, answer(question))
    resumed = start(world).json()

    passed = finish(world, attempt).json()
    failed = play(world, wrong={"SINGLE", "MULTIPLE", "TEXT"})

    assert all(item["correct_answer"] is None for item in resumed["answers"])
    by_question = {item["question"]: item for item in passed["review"]}
    single = attempt["questions"][0]
    assert by_question[single["id"]]["correct"] is False
    assert by_question[single["id"]]["correct_answer"] == shown_answer(single)
    assert by_question[single["id"]]["explanation"] == (
        "HTML — sahifa tuzilmasi uchun belgilash tili."
    )
    assert len(passed["review"]) == 5
    assert failed["passed"] is False and failed["review"] == []


def test_malformed_answers_are_rejected(world: World) -> None:
    attempt = start(world).json()
    single, multiple, text, order, match = attempt["questions"]
    bad: list[tuple[dict[str, Any], Any]] = [
        (single, {"choice": 99}),
        (single, {"choice": True}),
        (single, {"choice": "1"}),
        (multiple, {"choices": [[1]]}),
        (multiple, {"choices": [1, 1]}),
        (text, {"text": ["h1"]}),
        (text, {"text": "x" * 6000}),
        (order, {"order": [1, 2]}),
        (order, {"order": [1, 1, 2]}),
        (match, {"pairs": {"x": 1}}),
        (match, {"pairs": {"1": 9}}),
        (match, {"pairs": [1, 2]}),
        (single, "1"),
    ]

    for question, response in bad:
        result = reply(world, attempt, question, response)
        assert result.status_code == 400, (response, result.json())

    assert "Javob formati noto'g'ri." in str(reply(world, attempt, single, {"choice": 0}).json())
    assert not Answer.objects.exists()


def test_each_question_is_answered_once_and_not_after_finish(world: World) -> None:
    attempt = start(world).json()
    first, second = attempt["questions"][:2]
    assert reply(world, attempt, first, right_answer(first)).status_code == 200

    twice = reply(world, attempt, first, right_answer(first))
    stranger = reply(world, attempt, {"id": 999_999}, {"choice": 1})
    finish(world, attempt)
    late = reply(world, attempt, second, right_answer(second))

    assert twice.status_code == 400 and "javob berilgan" in str(twice.json())
    assert stranger.status_code == 400
    assert late.status_code == 400 and "yakunlangan" in str(late.json())


def test_finish_scores_stars_and_completes_lesson(world: World) -> None:
    attempt = start(world).json()
    for question in attempt["questions"]:
        answer = wrong_answer if question["kind"] == "MULTIPLE" else right_answer
        reply(world, attempt, question, answer(question))

    result = finish(world, attempt).json()
    again = finish(world, attempt).json()

    assert len(result.pop("review")) == 5
    assert result == {
        "score": 80,
        "stars": 2,
        "passed": True,
        "correct": 4,
        "total": 5,
        "best_score": 80,
        "best_stars": 2,
    }
    again.pop("review")
    assert again == result
    progress = LessonProgress.objects.get(user=world.student, lesson=world.quiz.lesson)
    assert progress.completed_at is not None


def test_failed_attempt_leaves_lesson_open(world: World) -> None:
    result = play(world, wrong={"SINGLE", "MULTIPLE", "TEXT", "ORDER"})

    assert (result["score"], result["stars"], result["passed"]) == (20, 0, False)
    assert not LessonProgress.objects.filter(completed_at__isnull=False).exists()


def test_best_result_counts_on_lesson_and_program(world: World) -> None:
    play(world, wrong={"MULTIPLE"})
    worse = play(world, wrong={"SINGLE", "TEXT", "ORDER"})

    assert (worse["score"], worse["stars"], worse["passed"]) == (40, 0, False)
    assert (worse["best_score"], worse["best_stars"]) == (80, 2)
    assert lesson_quiz(world) == {
        "id": world.quiz.pk,
        "title": "HTML asoslari",
        "questions": 5,
        "pass_percent": 70,
        "best_score": 80,
        "stars": 2,
        "passed": True,
        "attempts": 2,
        "in_progress": False,
        "telegram": False,
    }
    course = api(world.student).get(f"/api/v1/my/courses/{world.course.slug}/").json()
    [module] = course["modules"]
    assert [lesson["quiz_stars"] for lesson in module["lessons"]] == [2, None, None]


def test_untouched_quiz_shows_zero_stars(world: World) -> None:
    course = api(world.student).get(f"/api/v1/my/courses/{world.course.slug}/").json()

    assert course["modules"][0]["lessons"][0]["quiz_stars"] == 0
    assert lesson_quiz(world)["best_score"] is None


def test_started_attempt_is_in_progress(world: World) -> None:
    attempt = start(world).json()
    before = lesson_quiz(world)["in_progress"]
    question = attempt["questions"][0]
    reply(world, attempt, question, right_answer(question))

    assert (before, lesson_quiz(world)["in_progress"]) == (False, True)


def test_start_over_leaves_the_old_attempt_behind(world: World) -> None:
    first = start(world).json()
    question = first["questions"][0]
    reply(world, first, question, right_answer(question))

    play(world)  # "Boshidan boshlash": yangi urinish yakunlanadi, eskisi tashlab ketiladi

    assert lesson_quiz(world)["in_progress"] is False
    assert start(world).json()["id"] != first["id"]


def test_questions_are_drawn_from_the_bank(world: World) -> None:
    Quiz.objects.filter(pk=world.quiz.pk).update(questions_per_attempt=2, shuffle_questions=True)

    body = start(world).json()

    assert body["total"] == 2 and len({question["id"] for question in body["questions"]}) == 2
    assert lesson_quiz(world)["questions"] == 2


def test_quiz_without_questions_is_hidden(world: World) -> None:
    world.quiz.questions.all().delete()

    response = start(world)

    assert lesson_quiz(world) is None
    assert response.status_code == 400 and "savol yo'q" in str(response.json())


def test_deleted_question_is_not_counted(world: World) -> None:
    attempt = start(world).json()
    for question in attempt["questions"][:4]:
        reply(world, attempt, question, right_answer(question))
    Question.objects.filter(pk=attempt["questions"][4]["id"]).delete()

    resumed = start(world).json()
    result = finish(world, attempt).json()

    assert resumed["total"] == 4
    assert (result["score"], result["total"], result["stars"]) == (100, 4, 3)


def test_only_enrolled_students_play_their_own_attempts(world: World) -> None:
    outsider = make_user("+998901000003", Role.STUDENT)
    attempt = start(world).json()
    question = attempt["questions"][0]
    calls: list[Callable[[], Any]] = [
        lambda: reply(world, attempt, question, right_answer(question), user=outsider),
        lambda: finish(world, attempt, user=outsider),
    ]

    assert start(world, user=outsider).status_code == 403
    assert api().post(f"/api/v1/quizzes/{world.quiz.pk}/attempts/").status_code == 403
    assert [call().status_code for call in calls] == [404, 404]


def test_group_page_shows_quiz_results(world: World) -> None:
    play(world, wrong={"MULTIPLE"})
    play(world, wrong={"SINGLE", "TEXT", "ORDER"})

    body = api(world.teacher).get(f"/api/v1/teacher/groups/{world.group.pk}/").json()

    [student] = body["students"]
    assert (student["quiz_average"], student["quiz_passed"]) == (80, 1)
