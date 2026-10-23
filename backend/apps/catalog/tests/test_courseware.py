"""Kurs dasturini fayllardan joylash (`import_course`): yaratish, qayta import, mavjud darslar,
test va uy vazifasini ehtiyot qilish, tekshiruv."""

from pathlib import Path
from typing import Any

import pytest
from django.core.management import CommandError, call_command

from apps.catalog import courseware
from apps.catalog.models import Category, Course, Lesson, LessonSlides, Module
from apps.homework.models import Assignment
from apps.quizzes.models import Attempt, Quiz
from apps.users.models import User

pytestmark = pytest.mark.django_db

SLIDES = "# {title}\n\n---\n\n## Ikkinchi\n\n- bir\n- ikki\n\n---\n\n```python\nprint(1)\n```\n"
QUIZ = "? 2 + 2 nechaga teng?\n= 4\n\n? Python fayli kengaytmasi?\n+ .py\n- .txt\n"


def lesson_text(title: str, *, quiz: str = QUIZ, homework: str = "1) Ismingizni chiqaring.") -> str:
    parts = [
        f'+++\ntitle = "{title}"\nsummary = "Qisqa tavsif"\n+++\n',
        "::: slaydlar",
        SLIDES.format(title=title),
        "::: ustozga",
        "Avval misol, keyin amaliyot.",
    ]
    if quiz:
        parts += ["::: test", quiz]
    if homework:
        parts += ["::: uy-vazifasi", homework]
    return "\n".join(parts)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    folder = tmp_path / "python"
    module = folder / "01-asoslar"
    module.mkdir(parents=True)
    (folder / "_kurs.toml").write_text(
        'course = "python"\nmodules = ["01-asoslar"]\n', encoding="utf-8"
    )
    (module / "_modul.toml").write_text(
        'title = "Python asoslari"\nsummary = "1-oy"\n', encoding="utf-8"
    )
    (module / "01-kirish.md").write_text(lesson_text("1-mavzu: Kirish"), encoding="utf-8")
    (module / "02-sikl.md").write_text(lesson_text("2-mavzu: Sikllar"), encoding="utf-8")
    return tmp_path


@pytest.fixture
def course(db: Any) -> Course:
    category = Category.objects.create(slug="it", name_uz="IT")
    return Course.objects.create(slug="python", title_uz="Python", category=category)


def run(root: Path, **flags: Any) -> courseware.Report:
    return courseware.apply(courseware.read_course("python", root), **flags)


def test_import_creates_everything(root: Path, course: Course) -> None:
    report = run(root)

    module = Module.objects.get(course=course)
    assert module.title == "Python asoslari" and module.summary == "1-oy"
    first, second = Lesson.objects.filter(module=module).order_by("order")
    assert (first.title, first.order, first.content_key) == (
        "1-mavzu: Kirish",
        1,
        "python/01-asoslar/01-kirish",
    )
    assert second.order == 2
    assert len(first.slides.data) == 3
    assert first.slides.teacher_notes == "Avval misol, keyin amaliyot."
    assert Quiz.objects.get(lesson=first).questions.count() == 2
    assert Assignment.objects.get(lesson=first).instructions == "1) Ismingizni chiqaring."
    assert "+ dars: 1-mavzu: Kirish" in report.lines


def test_reimport_updates_slides_without_duplicates(root: Path, course: Course) -> None:
    run(root)
    path = root / "python" / "01-asoslar" / "01-kirish.md"
    path.write_text(
        lesson_text("1-mavzu: Kirish (yangi)").replace("- ikki\n", "- ikki\n- uch\n"),
        encoding="utf-8",
    )

    run(root)

    assert Lesson.objects.count() == 2
    lesson = Lesson.objects.get(content_key="python/01-asoslar/01-kirish")
    assert lesson.title == "1-mavzu: Kirish (yangi)"
    assert len(lesson.slides.data[1]["blocks"][0]["items"]) == 3
    assert Quiz.objects.get(lesson=lesson).questions.count() == 2  # test qayta qo'shilmadi


def test_reimport_refreshes_slides_rendered_by_older_version(root: Path, course: Course) -> None:
    run(root)
    assert "slaydlar yangilandi: 0 ta dars" in run(root).lines
    LessonSlides.objects.update(data=[])  # eski tuzilmada saqlangan

    report = run(root)

    assert all(len(item.data) == 3 for item in LessonSlides.objects.all())
    assert "slaydlar yangilandi: 2 ta dars" in report.lines


def test_existing_lesson_is_adopted_and_its_quiz_kept(root: Path, course: Course) -> None:
    module = Module.objects.create(course=course, title_uz="Python asoslari", order=1)
    old = Lesson.objects.create(module=module, title_uz="1-mavzu: Kirish", order=1)
    quiz = Quiz.objects.create(lesson=old, title="Eski test")
    courseware.import_questions(quiz, courseware.parse("? Eski savol?\n= ha\n"))

    run(root)

    old.refresh_from_db()
    assert old.content_key == "python/01-asoslar/01-kirish"
    assert Lesson.objects.filter(module=module).count() == 2
    assert [q.text for q in quiz.questions.all()] == ["Eski savol?"]
    assert LessonSlides.objects.filter(lesson=old).exists()


def test_replace_tests_refuses_when_attempts_exist(root: Path, course: Course) -> None:
    run(root)
    lesson = Lesson.objects.get(content_key="python/01-asoslar/01-kirish")
    student = User.objects.create_user(phone="+998901112233", password="x")
    Attempt.objects.create(quiz=lesson.quiz, student=student)

    report = run(root, replace_tests=True)

    assert "! test almashtirilmadi (urinishlar bor): 1-mavzu: Kirish" in report.lines
    assert "+ test: 2-mavzu: Sikllar — 2 savol" in report.lines


def test_homework_is_kept_unless_asked(root: Path, course: Course) -> None:
    run(root)
    path = root / "python" / "01-asoslar" / "01-kirish.md"
    path.write_text(lesson_text("1-mavzu: Kirish", homework="Yangi topshiriq"), encoding="utf-8")

    run(root)
    lesson = Lesson.objects.get(content_key="python/01-asoslar/01-kirish")
    assert lesson.assignment.instructions == "1) Ismingizni chiqaring."

    run(root, update_homework=True)
    lesson.assignment.refresh_from_db()
    assert lesson.assignment.instructions == "Yangi topshiriq"


def test_dry_run_writes_nothing(root: Path, course: Course) -> None:
    report = run(root, dry_run=True)

    assert not Lesson.objects.exists()
    assert report.lines[-1] == "(sinov: bazaga yozilmadi)"


def test_module_from_another_course_folder(root: Path, course: Course) -> None:
    backend = Course.objects.create(slug="backend", title_uz="Backend", category=course.category)
    folder = root / "backend"
    folder.mkdir()
    (folder / "_kurs.toml").write_text(
        'course = "backend"\nmodules = ["../python/01-asoslar"]\n', encoding="utf-8"
    )

    courseware.apply(courseware.read_course("backend", root))

    assert Lesson.objects.filter(module__course=backend).count() == 2
    assert Lesson.objects.filter(content_key="backend/01-asoslar/01-kirish").exists()


def test_problems_and_file_errors(root: Path, course: Course) -> None:
    module = root / "python" / "01-asoslar"
    (module / "03-xato.md").write_text(
        '+++\ntitle = "3-mavzu"\n+++\n::: slaydlar\nbitta\n::: test\n? Javobsiz savol\n',
        encoding="utf-8",
    )

    found = courseware.problems(courseware.read_course("python", root))

    assert any("03-xato.md: slaydlar 3 tadan kam" in line for line in found)
    assert any("03-xato.md: test" in line for line in found)

    (module / "04-bosh.md").write_text("::: slaydlar\n", encoding="utf-8")
    with pytest.raises(courseware.ContentError, match="«\\+\\+\\+» sarlavha"):
        courseware.read_course("python", root)


def test_unknown_section_and_missing_course(root: Path) -> None:
    path = root / "python" / "01-asoslar" / "01-kirish.md"
    path.write_text('+++\ntitle = "X"\n+++\n::: slayd\n', encoding="utf-8")
    with pytest.raises(courseware.ContentError, match="noma'lum bo'lim"):
        courseware.read_course("python", root)

    path.write_text(lesson_text("1-mavzu: Kirish"), encoding="utf-8")
    with pytest.raises(courseware.ContentError, match="kursi topilmadi"):
        run(root)


def test_command_checks_files(root: Path, course: Course, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(courseware, "CONTENT", root)

    call_command("import_course", "python", "--check")
    assert not Lesson.objects.exists()

    call_command("import_course", "python")
    assert Lesson.objects.count() == 2

    with pytest.raises(CommandError, match="Kurs nomi kerak"):
        call_command("import_course")


def test_repository_content_is_valid() -> None:
    """backend/content dagi hamma kurslar xatosiz o'qiladi (slaydlar, testlar)."""
    for name in courseware.course_names():
        content = courseware.read_course(name)
        assert courseware.problems(content) == [], name
