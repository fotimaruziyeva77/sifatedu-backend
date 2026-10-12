"""scripts/imtihon_python_qayta.py: bir necha o'quvchiga qayta imtihon — yangi amaliy topshiriqlar,
test oktabr imtihonining bankidan; guruhning qolganlariga ochilmaydi va xabar bormaydi."""

import os
from datetime import date, datetime
from pathlib import Path
from typing import Any
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.utils import timezone

from apps.bot.exam import open_exams
from apps.catalog.models import Category, Course, Lesson, Module
from apps.exams import services
from apps.exams.models import Exam, ExamExtension, ExamTask
from apps.learning.models import Enrollment
from apps.notifications.models import Notification
from apps.quizzes.models import Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import import_questions
from apps.users.models import User

from .conftest import SOURCE, make_user

pytestmark = pytest.mark.django_db

SCRIPT = Path(settings.BASE_DIR) / "scripts" / "imtihon_python_qayta.py"
TASHKENT = ZoneInfo("Asia/Tashkent")


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 12, hour, minute, tzinfo=TASHKENT)


def run(action: str, moment: datetime, **env: str) -> None:
    code = compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec")
    with (
        mock.patch.dict(os.environ, {"ACTION": action, **env}),
        mock.patch.object(timezone, "now", return_value=moment),
    ):
        exec(code, {"__name__": "imtihon_python_qayta"})  # noqa: S102 — serverda ham shunday


@pytest.fixture
def october(db: Any) -> Exam:
    category = Category.objects.create(slug="it", name_uz="IT")
    python = Course.objects.create(
        slug="python", title_uz="Python", category=category, status=Course.Status.PUBLISHED
    )
    module = Module.objects.create(course=python, title_uz="Oktabr imtihoni — savollar banki")
    lesson = Lesson.objects.create(module=module, title_uz="Savollar")
    import_questions(Quiz.objects.create(lesson=lesson, title="Bank"), parse(SOURCE))
    exam = Exam.objects.create(
        course=python,
        month=date(2026, 10, 1),
        status=Exam.Status.READY,
        questions_count=3,
        duration_min=30,
        pass_percent=60,
        test_weight=50,
        opens_at=datetime(2026, 10, 2, 17, 39, tzinfo=TASHKENT),
        closes_at=datetime(2026, 10, 2, 19, 23, tzinfo=TASHKENT),
    )
    exam.modules.set([module])
    ExamTask.objects.create(exam=exam, order=1, title="Eski topshiriq", instructions="a = 17")
    for phone, name in (("+998901000001", "Jahongir"), ("+998901000002", "Dilshod")):
        Enrollment.objects.create(
            user=make_user(phone, name=name), course=python, status=Enrollment.Status.ACTIVE
        )
    return exam


def test_retake_opens_only_for_the_listed_students(october: Exam, capsys: Any) -> None:
    run("open", at(19), PHONES="+998 90 100 00 01, 901009999", HOURS="3")
    run("open", at(19, 2), PHONES="+998901000001")  # qayta — ikkinchi xabar yo'q

    retake = Exam.objects.get(month=date(2026, 10, 12))
    assert retake.course == october.course and retake.is_ready
    assert (retake.questions_count, retake.duration_min, retake.pass_percent) == (3, 30, 60)
    assert list(retake.modules.all()) == list(october.modules.all())
    titles = list(retake.tasks.values_list("title", flat=True))
    assert len(titles) == 4 and titles[0] == "1. Arifmetik amallar: do'kon"
    assert october.tasks.get().title == "Eski topshiriq"  # oktabr imtihoni o'zgarmadi

    jahongir, dilshod = (
        User.objects.get(first_name="Jahongir"),
        User.objects.get(first_name="Dilshod"),
    )
    extension = ExamExtension.objects.get(exam=retake)
    assert (extension.student, extension.until) == (jahongir, at(22))
    with mock.patch.object(timezone, "now", return_value=at(19, 30)):
        assert services.available(retake, jahongir)
        assert not services.available(retake, dilshod)
        assert [exam.pk for exam in open_exams(jahongir)] == [retake.pk]
        assert open_exams(dilshod) == []
    assert services.announce_open(now=at(19, 5)) == 0  # guruhga «ochildi» xabari bormaydi
    sent = Notification.objects.filter(kind=Notification.Kind.EXAM_OPENED)
    assert list(sent.values_list("user__first_name", flat=True)) == ["Jahongir"]
    assert "22:00 gacha" in sent.get().body
    output = capsys.readouterr().out
    assert "+998901009999 — bunday o'quvchi topilmadi" in output

    run("add", at(20), PHONES="+998901000002")
    added = ExamExtension.objects.get(exam=retake, student=dilshod)
    assert added.until == at(22)  # muddat birinchilarniki bilan bir xil
    run("status", at(20, 30))
    assert "Dilshod" in capsys.readouterr().out
