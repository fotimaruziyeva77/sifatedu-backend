"""Qo'llanmadan AI test: qoralama yaratish (fayl + mavzu), tuzish (`tasks.generate_draft`) va
o'qituvchi tekshirgach e'lon qilish — savollar mavzu testiga qo'shiladi, mavzu guruh uchun
«o'tildi» bo'ladi va o'quvchilarga «Dars ochildi · Testni boshlash» xabari boradi.
"""

from datetime import datetime, timedelta
from typing import Any

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.catalog.models import Course, Lesson, LessonMaterial, Module

from . import ai
from .models import Quiz, QuizDraft
from .parser import parse
from .services import import_questions

STALE_AFTER = timedelta(minutes=5)  # Gemini 150 s da uziladi — undan ko'pi — vazifa yo'qolgan


class DraftError(ValueError):
    """O'qituvchiga ko'rsatiladigan sabab (API 400)."""


def check_file(upload: UploadedFile) -> None:
    if ai.suffix(upload.name or "") not in ai.ALLOWED:
        raise DraftError("PDF, Word (.docx), PowerPoint (.pptx), rasm yoki matn faylini yuklang.")
    if (upload.size or 0) > ai.MAX_BYTES:
        raise DraftError("Fayl 20 MB dan katta bo'lmasin.")


def new_topic(course: Course, title: str) -> Lesson:
    """Kursning oxirgi moduliga yangi dars (mavzu); modul bo'lmasa — «Darslar»."""
    module = Module.objects.filter(course=course).order_by("-order", "-id").first()
    if module is None:
        module = Module.objects.create(course=course, title_uz="Darslar")
    last = Lesson.objects.filter(module=module).aggregate(last=Max("order"))["last"] or 0
    return Lesson.objects.create(module=module, title_uz=title, order=last + 1)


def create(
    live_lesson: Any, *, by: Any, upload: UploadedFile, topic: Lesson | None, new_title: str = ""
) -> QuizDraft:
    from .tasks import generate_draft

    check_file(upload)
    if not ai.ready():
        raise DraftError("AI kaliti sozlanmagan: serverda GEMINI_API_KEY kiritilishi kerak.")
    with transaction.atomic():
        if topic is None:
            title = new_title.strip()
            if not title:
                raise DraftError("Mavzuni tanlang yoki yangi mavzu nomini yozing.")
            topic = new_topic(live_lesson.group.course, title[:200])
        elif topic.module.course_id != live_lesson.group.course_id:
            raise DraftError("Bu mavzu guruh kursiga tegishli emas.")
        draft = QuizDraft.objects.create(
            lesson=topic,
            live_lesson=live_lesson,
            file=upload,
            file_name=(upload.name or "qo'llanma")[:255],
            created_by=by,
        )
        transaction.on_commit(lambda: generate_draft.delay(draft.pk))
    return draft


def run(draft: QuizDraft) -> None:
    """Tuzish (Celery'da): fayl Gemini'ga, natija — «Tez kiritish» matni."""
    with draft.file.open("rb") as handle:
        data = handle.read()
    try:
        _topic, text = ai.generate(draft.file_name, data)
    except ai.AiError as exc:
        draft.status, draft.error = QuizDraft.Status.FAILED, str(exc)[:500]
    else:
        draft.status, draft.text, draft.error = QuizDraft.Status.READY, text, ""
    draft.save(update_fields=["status", "text", "error", "updated_at"])


def publish(draft: QuizDraft, *, by: Any, text: str, share_file: bool) -> dict[str, Any]:
    """Savollar mavzu testiga qo'shiladi; jonli dars bo'lsa — mavzu guruhda «o'tildi»."""
    if draft.status != QuizDraft.Status.READY:
        raise DraftError("Bu test allaqachon e'lon qilingan yoki hali tayyor emas.")
    drafts = parse(text)  # ParseError — qator raqamlari bilan
    with transaction.atomic():
        quiz, _created = Quiz.objects.get_or_create(lesson=draft.lesson)
        first = not quiz.questions.exists()
        count = import_questions(quiz, drafts)
        if share_file:
            material = LessonMaterial(
                lesson=draft.lesson, kind=LessonMaterial.Kind.FILE, title=draft.file_name[:200]
            )
            with draft.file.open("rb") as handle:
                material.file.save(draft.file_name, ContentFile(handle.read()), save=False)
            material.save()
        draft.status = QuizDraft.Status.PUBLISHED
        draft.text, draft.count, draft.published_at = text, count, timezone.now()
        draft.save(update_fields=["status", "text", "count", "published_at", "updated_at"])
    return {"count": count, **open_for_group(draft, by=by, first_questions=first)}


def open_for_group(draft: QuizDraft, *, by: Any, first_questions: bool) -> dict[str, bool]:
    """`covered` — mavzu guruhda ochiq (o'quvchilar testni hozir ishlay oladi); `notified` —
    hozir «Dars ochildi · Testni boshlash» xabari ketdi. Mavzu avval testsiz ochilgan bo'lsa
    (o'qituvchi oldin «Dars o'tildi» bosgan) — xabar endi, test tugmasi bilan boradi."""
    from apps.live import services as live
    from apps.live.models import GroupLesson

    lesson = draft.live_lesson
    if lesson is None:
        return {"covered": False, "notified": False}
    try:
        if live.cover(lesson, draft.lesson, by):
            return {"covered": True, "notified": True}
    except live.LiveError:
        pass  # dars hali boshlanmagan — o'qituvchi keyin «Dars o'tildi» bosadi
    record = GroupLesson.objects.filter(group=lesson.group, lesson=draft.lesson).first()
    if record is None:
        return {"covered": False, "notified": False}
    sent = live.announce(record, quiz_ready=True) if first_questions else 0
    return {"covered": True, "notified": sent > 0}


def expire(draft: QuizDraft, *, now: datetime | None = None) -> QuizDraft:
    """Ishchi qayta ishga tushsa (deploy), vazifa yo'qoladi: uzoq kutgan PENDING — FAILED,
    o'qituvchi faylni qayta yuklaydi (aks holda sahifa «AI tuzmoqda»da qolib ketadi)."""
    now = now or timezone.now()
    if draft.status == QuizDraft.Status.PENDING and draft.created_at < now - STALE_AFTER:
        draft.status = QuizDraft.Status.FAILED
        draft.error = "Jarayon to'xtab qoldi — faylni qayta yuklang."
        draft.save(update_fields=["status", "error", "updated_at"])
    return draft


def latest(live_lesson: Any) -> QuizDraft | None:
    draft = QuizDraft.objects.filter(live_lesson=live_lesson).select_related("lesson").first()
    return expire(draft) if draft else None


def payload(draft: QuizDraft | None) -> dict[str, Any] | None:
    if draft is None:
        return None
    return {
        "id": draft.pk,
        "status": draft.status,
        "lesson_id": draft.lesson_id,
        "lesson_title": str(draft.lesson.title),
        "file_name": draft.file_name,
        "text": draft.text,
        "error": draft.error,
        "count": draft.count,
        "created_at": draft.created_at,
    }
