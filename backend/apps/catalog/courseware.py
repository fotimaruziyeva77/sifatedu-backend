"""Kurs dasturini repodagi matn fayllaridan o'qish va platformaga joylash (`import_course`).

Tuzilma (`backend/content/`):

    <kurs>/_kurs.toml          course = "python"; modules = ["01-python-asoslari", ...]
                                (boshqa kursning moduli ham bo'ladi: "../python/01-python-asoslari")
    <kurs>/<NN-modul>/_modul.toml   title = "..."; summary = "..."
    <kurs>/<NN-modul>/<NN-dars>.md  dars: TOML sarlavha (+++ ... +++) va bo'limlar

Dars fayli bo'limlari (alohida qatorda, kod bloki tashqarisida):

    ::: slaydlar      — Markdown, slaydlar orasida `---`
    ::: ustozga       — ustozga eslatma (faqat o'qituvchi ko'radi)
    ::: test          — «Tez kiritish» formatidagi savollar
    ::: uy-vazifasi   — uy vazifasi matni

Dars tartibi — fayl nomidagi raqam. Qayta import xavfsiz: dars `content_key` bo'yicha (birinchi
marta — modul ichida nomi bo'yicha) topiladi va yangilanadi; mavjud test savollari va uy vazifasi
o'zgartirilmaydi (bayroqlar bilan — ataylab).
"""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings
from django.db import transaction

from apps.homework.models import Assignment
from apps.quizzes.models import Quiz
from apps.quizzes.parser import ParseError, parse
from apps.quizzes.services import import_questions

from . import slides as slide_kit
from .models import Course, Lesson, LessonSlides, Module

CONTENT = Path(settings.BASE_DIR) / "content"
SECTIONS = {"slaydlar": "slides", "ustozga": "notes", "test": "quiz", "uy-vazifasi": "homework"}
ORDER = re.compile(r"^(\d+)[-_]")
MIN_SLIDES = 3


class ContentError(ValueError):
    """Dastur fayllaridagi xato (fayl yo'li bilan)."""


@dataclass
class LessonFile:
    path: Path
    order: int
    key: str
    title: str
    summary: str = ""
    duration_min: int | None = None
    preview: bool = False
    homework_title: str = "Uy vazifasi"
    slides: str = ""
    notes: str = ""
    quiz: str = ""
    homework: str = ""


@dataclass
class ModuleDir:
    path: Path
    order: int
    title: str
    summary: str
    lessons: list[LessonFile] = field(default_factory=list)


@dataclass
class CourseContent:
    name: str
    slug: str
    modules: list[ModuleDir]


def toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ContentError(f"{path}: {exc}") from exc


def front_matter(path: Path, text: str) -> tuple[dict, str]:
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "+++":
        raise ContentError(f"{path}: fayl «+++» sarlavha bilan boshlanishi kerak")
    try:
        end = next(k for k in range(1, len(lines)) if lines[k].strip() == "+++")
    except StopIteration as exc:
        raise ContentError(f"{path}: sarlavha yopilmagan («+++»)") from exc
    try:
        meta = tomllib.loads("\n".join(lines[1:end]))
    except tomllib.TOMLDecodeError as exc:
        raise ContentError(f"{path}: sarlavhada xato: {exc}") from exc
    return meta, "\n".join(lines[end + 1 :])


def sections(path: Path, body: str) -> dict[str, str]:
    found: dict[str, list[str]] = {}
    current: list[str] | None = None
    fence = ""
    for line in body.split("\n"):
        stripped = line.strip()
        if fence:
            if stripped.startswith(fence):
                fence = ""
        elif stripped.startswith(("```", "~~~")):
            fence = stripped[:3]
        elif stripped.startswith(":::"):
            name = stripped[3:].strip().lower()
            if name not in SECTIONS:
                raise ContentError(f"{path}: noma'lum bo'lim «{stripped}»")
            if SECTIONS[name] in found:
                raise ContentError(f"{path}: «{stripped}» ikki marta")
            current = found.setdefault(SECTIONS[name], [])
            continue
        if current is not None:
            current.append(line)
    return {key: "\n".join(lines).strip() for key, lines in found.items()}


def read_lesson(path: Path, module_key: str) -> LessonFile:
    match = ORDER.match(path.name)
    if match is None:
        raise ContentError(f"{path}: fayl nomi raqam bilan boshlanishi kerak (08-for-sikli.md)")
    meta, body = front_matter(path, path.read_text(encoding="utf-8"))
    title = str(meta.get("title", "")).strip()
    if not title or len(title) > 200:
        raise ContentError(f"{path}: title (1–200 belgi) kerak")
    parts = sections(path, body)
    return LessonFile(
        path=path,
        order=int(match.group(1)),
        key=f"{module_key}/{path.stem}",
        title=title,
        summary=str(meta.get("summary", "")).strip()[:300],
        duration_min=int(meta["duration_min"]) if "duration_min" in meta else None,
        preview=bool(meta.get("preview", False)),
        homework_title=str(meta.get("homework_title", "Uy vazifasi")).strip()[:200],
        slides=parts.get("slides", ""),
        notes=parts.get("notes", ""),
        quiz=parts.get("quiz", ""),
        homework=parts.get("homework", ""),
    )


def read_module(path: Path, order: int) -> ModuleDir:
    meta = toml(path / "_modul.toml")
    title = str(meta.get("title", "")).strip()
    if not title:
        raise ContentError(f"{path / '_modul.toml'}: title kerak")
    module = ModuleDir(
        path=path, order=order, title=title, summary=str(meta.get("summary", ""))[:300]
    )
    module.lessons = sorted(
        (
            read_lesson(item, path.name)
            for item in path.glob("*.md")
            if not item.name.startswith("_")
        ),
        key=lambda lesson: lesson.order,
    )
    orders = [lesson.order for lesson in module.lessons]
    if len(set(orders)) != len(orders):
        raise ContentError(f"{path}: darslar tartib raqami takrorlangan")
    return module


def read_course(name: str, root: Path | None = None) -> CourseContent:
    folder = (root or CONTENT) / name
    meta = toml(folder / "_kurs.toml")
    slug = str(meta.get("course", "")).strip()
    if not slug:
        raise ContentError(f"{folder / '_kurs.toml'}: course (kurs slug'i) kerak")
    modules = [
        read_module((folder / str(item)).resolve(), order)
        for order, item in enumerate(meta.get("modules", []), start=1)
    ]
    return CourseContent(name=name, slug=slug, modules=modules)


def course_names(root: Path | None = None) -> list[str]:
    return sorted(item.parent.name for item in (root or CONTENT).glob("*/_kurs.toml"))


def problems(content: CourseContent) -> list[str]:
    """Bazaga yozmasdan tekshiruv: slaydlar, test va uy vazifasi o'qiladimi."""
    found = []
    for module in content.modules:
        for lesson in module.lessons:
            where = lesson.path.relative_to(lesson.path.parents[2])
            if not lesson.slides:
                found.append(f"{where}: slaydlar yo'q")
            elif len(slide_kit.split(lesson.slides)) < MIN_SLIDES:
                found.append(f"{where}: slaydlar {MIN_SLIDES} tadan kam")
            else:
                slide_kit.render(lesson.slides)
            if lesson.quiz:
                try:
                    parse(lesson.quiz)
                except ParseError as exc:
                    found += [f"{where}: test, {error}" for error in exc.errors]
    return found


@dataclass
class Report:
    lines: list[str] = field(default_factory=list)

    def add(self, line: str) -> None:
        self.lines.append(line)


def sync_module(course: Course, module_dir: ModuleDir, report: Report) -> Module:
    module = Module.objects.filter(course=course, title=module_dir.title).first()
    if module is None:
        module = Module.objects.create(
            course=course,
            title=module_dir.title,
            summary=module_dir.summary,
            order=module_dir.order,
        )
        report.add(f"+ modul: {module_dir.title}")
        return module
    changed = []
    if module.order != module_dir.order:
        module.order = module_dir.order
        changed.append("order")
    if module_dir.summary and module.summary != module_dir.summary:
        module.summary = module_dir.summary
        changed.append("summary")
    if changed:
        module.save(update_fields=[*changed, "updated_at"])
    return module


def sync_lesson(course: Course, module: Module, item: LessonFile, report: Report) -> Lesson:
    key = f"{course.slug}/{item.key}"
    lesson = (
        Lesson.objects.filter(module__course=course, content_key=key).first()
        or Lesson.objects.filter(module=module, title=item.title).first()
    )
    values = {
        "module": module,
        "title": item.title,
        "summary": item.summary,
        "order": item.order,
        "content_key": key,
    }
    if item.duration_min is not None:
        values["duration_min"] = item.duration_min
    if item.preview:
        values["is_preview"] = True
    if lesson is None:
        lesson = Lesson.objects.create(**values)
        report.add(f"+ dars: {item.title}")
        return lesson
    changed = [name for name, value in values.items() if getattr(lesson, name) != value]
    for name in changed:
        setattr(lesson, name, values[name])
    if changed:
        lesson.save(update_fields=[*changed, "updated_at"])
        report.add(f"~ dars: {item.title} ({', '.join(changed)})")
    return lesson


def sync_quiz(lesson: Lesson, item: LessonFile, replace: bool, report: Report) -> None:
    if not item.quiz:
        return
    quiz, _created = Quiz.objects.get_or_create(
        lesson=lesson, defaults={"title": f"{item.title} — test"}
    )
    has_questions = quiz.questions.exists()
    if has_questions and not replace:
        return
    if has_questions and quiz.attempts.exists():
        report.add(f"! test almashtirilmadi (urinishlar bor): {item.title}")
        return
    if has_questions:
        quiz.questions.all().delete()
    count = import_questions(quiz, parse(item.quiz))
    report.add(f"+ test: {item.title} — {count} savol")


def sync_homework(lesson: Lesson, item: LessonFile, update: bool, report: Report) -> None:
    if not item.homework:
        return
    assignment = Assignment.objects.filter(lesson=lesson).first()
    if assignment is None:
        Assignment.objects.create(
            lesson=lesson, title=item.homework_title, instructions=item.homework
        )
        report.add(f"+ uy vazifasi: {item.title}")
    elif update and (
        assignment.instructions != item.homework or assignment.title != item.homework_title
    ):
        assignment.title = item.homework_title
        assignment.instructions = item.homework
        assignment.save(update_fields=["title", "instructions", "updated_at"])
        report.add(f"~ uy vazifasi: {item.title}")


def apply(
    content: CourseContent,
    *,
    replace_tests: bool = False,
    update_homework: bool = False,
    dry_run: bool = False,
) -> Report:
    """Platformaga joylash. Kurs oldindan bo'lishi kerak (admin'da yaratiladi)."""
    report = Report()
    course = Course.objects.filter(slug=content.slug).first()
    if course is None:
        raise ContentError(f"«{content.slug}» kursi topilmadi — avval admin panelda yarating")
    with transaction.atomic():
        slides_changed = 0
        for module_dir in content.modules:
            module = sync_module(course, module_dir, report)
            for item in module_dir.lessons:
                lesson = sync_lesson(course, module, item, report)
                if item.slides:
                    current = LessonSlides.objects.filter(lesson=lesson).first()
                    # Matn o'zgarmasa ham: slayd tuzilmasi (render) yangilangan bo'lishi mumkin.
                    if (
                        current is None
                        or (current.markdown, current.teacher_notes) != (item.slides, item.notes)
                        or current.data != slide_kit.render(item.slides)
                    ):
                        LessonSlides.objects.update_or_create(
                            lesson=lesson,
                            defaults={"markdown": item.slides, "teacher_notes": item.notes},
                        )
                        slides_changed += 1
                sync_quiz(lesson, item, replace_tests, report)
                sync_homework(lesson, item, update_homework, report)
        report.add(f"slaydlar yangilandi: {slides_changed} ta dars")
        if dry_run:
            transaction.set_rollback(True)
            report.add("(sinov: bazaga yozilmadi)")
    return report
