"""Admin: tez kiritish, variantlar tekshiruvi, o'qituvchi faqat o'z testlari, savol statistikasi."""

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from apps.quizzes.models import Answer, Attempt, Question, Quiz
from apps.users.models import User
from apps.users.roles import Role

from .conftest import World, instructor, make_user

pytestmark = pytest.mark.django_db


def login(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def management(prefix: str, total: int = 0, initial: int = 0) -> dict[str, Any]:
    return {
        f"{prefix}-TOTAL_FORMS": str(total),
        f"{prefix}-INITIAL_FORMS": str(initial),
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


def quiz_form(world: World, quick: str) -> dict[str, Any]:
    return {
        "lesson": world.lessons[1].pk,
        "title": "CSS asoslari",
        "pass_percent": "70",
        "questions_per_attempt": "0",
        "shuffle_questions": "on",
        "quick": quick,
        **management("questions"),
    }


def test_quick_import_adds_questions(world: World) -> None:
    instructor(world.teacher, world.course)
    client = login(world.teacher)

    response = client.post(
        reverse("admin:quizzes_quiz_add"),
        quiz_form(world, "? Rang qaysi xususiyat?\n+ color\n- font-size\n\n? Qalin?\n= bold\n"),
        follow=True,
    )

    assert response.status_code == 200
    quiz = Quiz.objects.get(lesson=world.lessons[1])
    assert [(item.kind, item.order) for item in quiz.questions.all()] == [
        ("SINGLE", 1),
        ("TEXT", 2),
    ]
    assert "2 ta savol qo&#x27;shildi." in response.content.decode()


def test_quick_import_errors_keep_the_form(world: World) -> None:
    response = login(make_admin()).post(
        reverse("admin:quizzes_quiz_add"), quiz_form(world, "? Chala savol\n+ Yolg'iz variant\n")
    )

    assert response.status_code == 200
    assert "1-qator: Kamida 2 ta variant kerak." in response.content.decode()
    assert not Quiz.objects.filter(lesson=world.lessons[1]).exists()


def make_admin() -> User:
    return User.objects.create_superuser(phone="+998900000009", password="x")


def question_form(question: Question, *choices: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {
        "quiz": question.quiz_id,
        "kind": question.kind,
        "text": question.text,
        "code": "",
        "language": "",
        "explanation": "",
        **management("choices", total=len(choices)),
    }
    for index, choice in enumerate(choices):
        data.update({f"choices-{index}-{key}": value for key, value in choice.items()})
        data[f"choices-{index}-order"] = str(index + 1)
        data[f"choices-{index}-question"] = str(question.pk)
    return data


def test_choices_must_fit_the_question_kind(world: World) -> None:
    question = Question.objects.create(quiz=world.quiz, kind=Question.Kind.SINGLE, text="Yangi")
    client = login(make_admin())
    url = reverse("admin:quizzes_question_change", args=[question.pk])

    two_right = client.post(
        url,
        question_form(
            question, {"text": "A", "is_correct": "on"}, {"text": "B", "is_correct": "on"}
        ),
    )
    fine = client.post(
        url, question_form(question, {"text": "A", "is_correct": "on"}, {"text": "B"})
    )

    assert two_right.status_code == 200
    assert "aynan 1 ta variant to&#x27;g&#x27;ri" in two_right.content.decode()
    assert fine.status_code == 302
    assert [(item.text, item.is_correct) for item in question.choices.all()] == [
        ("A", True),
        ("B", False),
    ]


def test_teacher_sees_only_own_quizzes(world: World) -> None:
    instructor(world.teacher, world.course)
    other = make_user("+998901000006", Role.TEACHER)
    Attempt.objects.create(quiz=world.quiz, student=world.student, score=80, stars=2, passed=True)

    for user, expected in ((world.teacher, 1), (other, 0)):
        client = login(user)
        for name in ("admin:quizzes_quiz_changelist", "admin:quizzes_attempt_changelist"):
            page = client.get(reverse(name))
            assert page.status_code == 200
            assert len(page.context["cl"].result_list) == expected
    assert login(other).get(
        reverse("admin:quizzes_quiz_change", args=[world.quiz.pk])
    ).status_code in (
        302,
        404,
    )


def test_lesson_admin_has_quiz_inline(world: World) -> None:
    instructor(world.teacher, world.course)

    page = login(world.teacher).get(
        reverse("admin:catalog_lesson_change", args=[world.lessons[0].pk])
    )

    assert page.status_code == 200
    assert Quiz in [inline.formset.model for inline in page.context["inline_admin_formsets"]]


def test_quiz_page_shows_per_question_results(world: World) -> None:
    first = world.quiz.questions.first()
    assert first is not None
    for correct in (True, False):
        attempt = Attempt.objects.create(quiz=world.quiz, student=world.student)
        Answer.objects.create(attempt=attempt, question=first, correct=correct)

    page = login(make_admin()).get(reverse("admin:quizzes_quiz_change", args=[world.quiz.pk]))

    content = page.content.decode()
    stats = content[content.index("Savollar bo&#x27;yicha") :]
    row = stats[stats.index("HTML nimaning qisqartmasi?") :]
    assert row.index("2") < row.index("50%") < row.index("Qaysilari HTML teglari?")
    # Savol qatorida variantlarga olib boradigan havola doim ko'rinadi.
    link = reverse("admin:quizzes_question_change", args=[first.pk])
    assert f'href="{link}"' in content and "3 ta — o&#x27;zgartirish ›" in content
