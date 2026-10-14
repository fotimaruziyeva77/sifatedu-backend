"""Qo'llanmadan AI test: fayldan matn, AI javobini «Tez kiritish»ga aylantirish, o'qituvchi
yuklaydi → tekshiradi → e'lon qiladi (mavzu «o'tildi», o'quvchilarga xabar)."""

import io
import zipfile
from datetime import timedelta
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, Lesson, LessonMaterial, Module
from apps.learning.models import Enrollment, StudyGroup
from apps.live.models import GroupLesson, LiveLesson
from apps.notifications.models import Notification
from apps.quizzes import ai
from apps.quizzes.models import Question, QuizDraft
from apps.quizzes.parser import parse
from apps.users.models import User
from apps.users.roles import Role, set_roles

pytestmark = pytest.mark.django_db


def person(phone: str, *roles: str, name: str = "Aziz") -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name=name)
    set_roles(user, roles)
    return user


def api(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def office(name: str, parts: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for part, xml in parts.items():
            archive.writestr(part, xml)
    return buffer.getvalue()


def quiz(*questions: ai.GenQuestion) -> ai.GenQuiz:
    return ai.GenQuiz(topic="Ro‘yxatlar", questions=list(questions))


def single(text: str, correct: str = "4", code: str = "") -> ai.GenQuestion:
    options = [ai.GenOption(text=value, correct=value == correct) for value in ("3", "4", "5")]
    return ai.GenQuestion(
        kind="single",
        text=text,
        code=code,
        language="python" if code else "",
        options=options,
        answers=[],
        explanation="Uzunlik — elementlar soni.",
    )


@pytest.fixture
def lesson(db: Any) -> LiveLesson:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(slug="python", title_uz="Python", category=category)
    module = Module.objects.create(course=course, title_uz="Asoslar")
    Lesson.objects.create(module=module, title_uz="O‘zgaruvchilar", order=1)
    teacher = person("+998903000001", Role.TEACHER, name="Ustoz")
    group = StudyGroup.objects.create(
        course=course, teacher=teacher, name="Python-1", status=StudyGroup.Status.ACTIVE
    )
    for phone in ("+998901000001", "+998901000002"):
        Enrollment.objects.create(user=person(phone, Role.STUDENT), course=course, group=group)
    return LiveLesson.objects.create(
        group=group, starts_at=timezone.now() - timedelta(hours=1), duration_min=90
    )


def test_office_text_reads_word_and_powerpoint() -> None:
    docx = office(
        "dars.docx",
        {
            "word/document.xml": (
                "<w:document><w:body><w:p><w:pPr/><w:r><w:t>Ro‘yxat — </w:t></w:r>"
                '<w:r><w:t xml:space="preserve">len(x) &amp; append</w:t></w:r></w:p>'
                "<w:p/><w:p><w:r><w:t>Ikkinchi xatboshi</w:t></w:r></w:p></w:body></w:document>"
            )
        },
    )
    pptx = office(
        "dars.pptx",
        {
            "ppt/slides/slide10.xml": "<p:sld><a:p><a:r><a:t>O‘ninchi</a:t></a:r></a:p></p:sld>",
            "ppt/slides/slide2.xml": "<p:sld><a:p><a:r><a:t>Ikkinchi</a:t></a:r></a:p></p:sld>",
        },
    )

    assert ai.office_text("dars.docx", docx) == "Ro‘yxat — len(x) & append\nIkkinchi xatboshi"
    assert ai.office_text("dars.pptx", pptx) == "Ikkinchi\nO‘ninchi"
    with pytest.raises(ai.AiError):
        ai.office_text("buzuq.docx", b"not a zip")


def test_ai_answer_becomes_quick_input_text_and_bad_questions_are_dropped() -> None:
    broken = ai.GenQuestion(
        kind="single",
        text="To'g'ri javobsiz",
        code="",
        language="",
        options=[ai.GenOption(text="a", correct=False), ai.GenOption(text="b", correct=False)],
        answers=[],
        explanation="",
    )
    typed = ai.GenQuestion(
        kind="text",
        text="print(len([1, 2]))\n natijasi?",
        code="",
        language="",
        options=[],
        answers=["2"],
        explanation="",
    )

    text = ai.to_text(
        quiz(single("Uzunlik?", code="x = [1, 2, 3, 4]\nprint(len(x))"), broken, typed)
    )

    drafts = parse(text)
    assert [d.kind for d in drafts] == [Question.Kind.SINGLE, Question.Kind.TEXT]
    assert (
        drafts[0].code == ["x = [1, 2, 3, 4]", "print(len(x))"] and drafts[0].language == "python"
    )
    assert drafts[1].text == "print(len([1, 2])) natijasi?"
    with pytest.raises(ai.AiError):
        ai.to_text(quiz(broken))


@override_settings(GEMINI_API_KEY="test-key")
def test_teacher_uploads_handout_reviews_and_publishes(
    lesson: LiveLesson, monkeypatch: pytest.MonkeyPatch, django_capture_on_commit_callbacks: Any
) -> None:
    seen: list[Any] = []

    def fake_model(parts: list[Any]) -> ai.GenQuiz:
        seen.append(parts)
        return quiz(single("Ro'yxatda nechta element?"), single("len([1,2,3,4])?"))

    monkeypatch.setattr(ai, "call_model", fake_model)
    client = api(lesson.group.teacher)
    upload = SimpleUploadedFile("royxatlar.pdf", b"%PDF-1.4 dars", content_type="application/pdf")

    with django_capture_on_commit_callbacks(execute=True):
        created = client.post(
            f"/api/v1/teacher/live/{lesson.pk}/quiz-drafts/",
            {"file": upload, "new_title": "Ro‘yxatlar"},
            format="multipart",
        )

    assert created.status_code == 201, created.json()
    assert created.json()["status"] == "PENDING" and created.json()["lesson_title"] == "Ro‘yxatlar"
    assert seen[0][0].inline_data.mime_type == "application/pdf"
    draft = client.get(f"/api/v1/teacher/quiz-drafts/{created.json()['id']}/").json()
    assert draft["status"] == "READY" and draft["text"].count("? ") == 2
    page = client.get(f"/api/v1/teacher/live/{lesson.pk}/").json()
    assert page["quiz_draft"]["id"] == draft["id"] and page["ai_ready"] is True

    edited = draft["text"] + "\n\n? Python'da ro'yxat qaysi qavsda yoziladi?\n+ []\n- {}\n"
    published = client.post(
        f"/api/v1/teacher/quiz-drafts/{draft['id']}/publish/",
        {"text": edited, "share_file": True},
        format="json",
    )

    assert published.status_code == 200, published.json()
    body = published.json()
    assert (body["count"], body["covered"], body["notified"]) == (3, True, True)
    assert body["draft"]["status"] == "PUBLISHED"
    topic = Lesson.objects.get(title_uz="Ro‘yxatlar")
    assert topic.quiz.questions.count() == 3
    assert LessonMaterial.objects.get(lesson=topic).title == "royxatlar.pdf"
    assert GroupLesson.objects.filter(group=lesson.group, lesson=topic).exists()
    opened = Notification.objects.filter(kind=Notification.Kind.LESSON_OPENED)
    assert opened.count() == 2 and all(item.quiz_id == topic.quiz.pk for item in opened)
    again = client.post(
        f"/api/v1/teacher/quiz-drafts/{draft['id']}/publish/", {"text": edited}, format="json"
    )
    assert again.status_code == 400


def ready_draft(lesson: LiveLesson, topic: Lesson, text: str) -> QuizDraft:
    return QuizDraft.objects.create(
        lesson=topic,
        live_lesson=lesson,
        file=SimpleUploadedFile("a.txt", b"x"),
        file_name="a.txt",
        status=QuizDraft.Status.READY,
        text=text,
        created_by=lesson.group.teacher,
    )


def test_topic_covered_before_the_quiz_is_announced_with_the_test_once(
    lesson: LiveLesson,
) -> None:
    from apps.live import services as live

    topic = Lesson.objects.get(title_uz="O‘zgaruvchilar")
    assert live.cover(lesson, topic, lesson.group.teacher)  # «Dars o'tildi» — test hali yo'q
    opened = Notification.objects.filter(kind=Notification.Kind.LESSON_OPENED)
    assert list(opened.values_list("quiz_id", flat=True)) == [None, None]
    client = api(lesson.group.teacher)
    results = []

    for text in ("? A\n+ ha\n- yo‘q", "? B\n+ ha\n- yo‘q"):
        draft = ready_draft(lesson, topic, text)
        url = f"/api/v1/teacher/quiz-drafts/{draft.pk}/publish/"
        results.append(client.post(url, {"text": text}, format="json").json())

    first, second = results
    assert (first["covered"], first["notified"]) == (True, True)
    assert (second["covered"], second["notified"]) == (True, False)
    with_test = opened.filter(quiz_id=topic.quiz.pk)
    assert with_test.count() == 2 and opened.count() == 4
    assert all(item.title.startswith("Test tayyor") for item in with_test)
    assert topic.quiz.questions.count() == 2


def test_publish_before_the_lesson_starts_waits_for_cover(lesson: LiveLesson) -> None:
    lesson.starts_at = timezone.now() + timedelta(days=1)
    lesson.save(update_fields=["starts_at"])
    topic = Lesson.objects.get(title_uz="O‘zgaruvchilar")
    draft = ready_draft(lesson, topic, "? A\n+ ha\n- yo‘q")

    body = (
        api(lesson.group.teacher)
        .post(
            f"/api/v1/teacher/quiz-drafts/{draft.pk}/publish/",
            {"text": "? A\n+ ha\n- yo‘q"},
            format="json",
        )
        .json()
    )

    assert (body["count"], body["covered"], body["notified"]) == (1, False, False)
    assert not GroupLesson.objects.exists() and not Notification.objects.exists()


def test_lost_generation_turns_into_an_error_so_the_teacher_can_retry(lesson: LiveLesson) -> None:
    topic = Lesson.objects.get(title_uz="O‘zgaruvchilar")
    lost = ready_draft(lesson, topic, "")
    fresh = ready_draft(lesson, topic, "")
    QuizDraft.objects.filter(pk__in=[lost.pk, fresh.pk]).update(status=QuizDraft.Status.PENDING)
    QuizDraft.objects.filter(pk=lost.pk).update(created_at=timezone.now() - timedelta(minutes=6))
    client = api(lesson.group.teacher)

    stale = client.get(f"/api/v1/teacher/quiz-drafts/{lost.pk}/").json()
    waiting = client.get(f"/api/v1/teacher/quiz-drafts/{fresh.pk}/").json()

    assert stale["status"] == "FAILED" and "qayta yuklang" in stale["error"]
    assert waiting["status"] == "PENDING"


@override_settings(GEMINI_API_KEY="test-key")
def test_publish_shows_parse_errors_and_strangers_see_nothing(lesson: LiveLesson) -> None:
    topic = Lesson.objects.get(title_uz="O‘zgaruvchilar")
    draft = QuizDraft.objects.create(
        lesson=topic,
        live_lesson=lesson,
        file=SimpleUploadedFile("a.txt", b"x"),
        file_name="a.txt",
        status=QuizDraft.Status.READY,
        text="? Savol\n+ ha\n- yo'q",
        created_by=lesson.group.teacher,
    )
    client = api(lesson.group.teacher)

    bad = client.post(
        f"/api/v1/teacher/quiz-drafts/{draft.pk}/publish/",
        {"text": "? Savol\nnimadir"},
        format="json",
    )

    assert bad.status_code == 400
    assert "2-qator" in str(bad.json())
    stranger = api(person("+998903000009", Role.TEACHER))
    assert stranger.get(f"/api/v1/teacher/quiz-drafts/{draft.pk}/").status_code == 404
    assert (
        stranger.post(
            f"/api/v1/teacher/live/{lesson.pk}/quiz-drafts/",
            {"file": SimpleUploadedFile("b.pdf", b"%PDF"), "lesson": topic.pk},
            format="multipart",
        ).status_code
        == 404
    )


def test_upload_needs_ai_key_and_a_supported_file(lesson: LiveLesson) -> None:
    client = api(lesson.group.teacher)
    topic = Lesson.objects.get(title_uz="O‘zgaruvchilar")

    no_key = client.post(
        f"/api/v1/teacher/live/{lesson.pk}/quiz-drafts/",
        {"file": SimpleUploadedFile("dars.pdf", b"%PDF"), "lesson": topic.pk},
        format="multipart",
    )
    with override_settings(GEMINI_API_KEY="test-key"):
        bad_type = client.post(
            f"/api/v1/teacher/live/{lesson.pk}/quiz-drafts/",
            {"file": SimpleUploadedFile("dars.exe", b"MZ"), "lesson": topic.pk},
            format="multipart",
        )

    assert no_key.status_code == 400 and "GEMINI_API_KEY" in str(no_key.json())
    assert bad_type.status_code == 400 and "PDF" in str(bad_type.json())
    assert not QuizDraft.objects.exists()
