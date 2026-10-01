"""Oylik imtihon jarayoni: tayyorlash, ochilish, test (javob paytida natijasiz), amaliy
topshiriqlar, baholash va yakuniy natija.

Vaqt qoidalari: imtihon oyning 25-kunidan oy oxirigacha ochiq (Toshkent vaqti). Test urinishi
boshlangach `duration_min` daqiqa (lekin imtihon yopilishidan oshmaydi). Alohida muddat berilgan
o'quvchi uchun imtihon o'sha muddatgacha ochiq.
"""

import calendar
import random
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.catalog.models import Course
from apps.catalog.scope import teacher_courses
from apps.core import events
from apps.homework.files import CheckedFile
from apps.learning.models import Enrollment, StudyGroup
from apps.live.models import GroupLesson
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.notifications.texts import day_month, locale_of, text
from apps.quizzes import grading
from apps.quizzes.models import Question, Quiz
from apps.quizzes.services import Layout, load_questions, result_payload
from apps.users.models import User
from apps.users.roles import sees_all

from .models import (
    Exam,
    ExamAnswer,
    ExamAttempt,
    ExamExtension,
    ExamResult,
    ExamTask,
    TaskAnswer,
    TaskAnswerFile,
)

OPEN_DAY = 25
DRAFT_DAY = 20
# Yopilgan imtihonlar natijasi shuncha kun davomida yakunlanadi (kechikkan baholar uchun).
FINALIZE_WITHIN = timedelta(days=45)
MAX_TEXT = 500


class ExamError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan sabab bilan (API 400)."""


# --- Vaqt ---


def month_start(day: date) -> date:
    return day.replace(day=1)


def window(month: date) -> tuple[datetime, datetime]:
    """Imtihon oynasi: 25-kun 00:00 dan keyingi oyning 1-kuni 00:00 gacha (mahalliy vaqt)."""
    last = calendar.monthrange(month.year, month.month)[1]
    opens = timezone.make_aware(datetime.combine(month.replace(day=min(OPEN_DAY, last)), time.min))
    closes = timezone.make_aware(datetime.combine(month.replace(day=last), time.min)) + timedelta(
        days=1
    )
    return opens, closes


def period(exam: Exam, locale: str) -> str:
    """ "25-oktabr — 31-oktabr" (o'quvchi tilida)."""
    first = timezone.localtime(exam.opens_at).date()
    last = timezone.localtime(exam.closes_at - timedelta(minutes=1)).date()
    return f"{day_month(first, locale)} — {day_month(last, locale)}"


# --- Kim qatnashadi ---


def participants(exam: Exam, *, now: datetime | None = None) -> QuerySet[User]:
    """Kursning faol o'quvchilari (guruhli va guruhsiz), xodimlarsiz."""
    now = now or timezone.now()
    return (
        User.objects.filter(
            Q(enrollments__course_id=exam.course_id)
            & Q(enrollments__status=Enrollment.Status.ACTIVE)
            & (Q(enrollments__expires_at__isnull=True) | Q(enrollments__expires_at__gt=now)),
            is_active=True,
            is_staff=False,
        )
        .distinct()
        .order_by("first_name", "last_name", "pk")
    )


def extension_for(exam: Exam, user: Any) -> ExamExtension | None:
    return ExamExtension.objects.filter(exam=exam, student_id=user.pk).first()


def window_end(exam: Exam, user: Any) -> datetime:
    extension = extension_for(exam, user)
    if extension is not None and extension.until > exam.closes_at:
        return extension.until
    return exam.closes_at


def is_participant(exam: Exam, user: Any) -> bool:
    return (
        participants(exam).filter(pk=user.pk).exists()
        or ExamExtension.objects.filter(exam=exam, student_id=user.pk).exists()
    )


def available(exam: Exam, user: Any, *, now: datetime | None = None) -> bool:
    """O'quvchi hozir test ishlay oladimi va topshiriq yubora oladimi."""
    now = now or timezone.now()
    return (
        exam.is_ready
        and exam.opens_at <= now < window_end(exam, user)
        and is_participant(exam, user)
    )


def revealed(exam: Exam, user: Any, *, now: datetime | None = None) -> bool:
    """To'g'ri javoblar ko'rsatiladimi: imtihon (va alohida muddat) yopilgach."""
    return (now or timezone.now()) >= window_end(exam, user)


def exams_for(user: Any, *, now: datetime | None = None) -> list[Exam]:
    """O'quvchining imtihonlari: ochiq, yaqinda yopilgan (natija uchun) va alohida muddatlilar."""
    now = now or timezone.now()
    course_ids = set(
        Enrollment.objects.filter(user_id=user.pk, status=Enrollment.Status.ACTIVE).values_list(
            "course_id", flat=True
        )
    )
    recent = now - FINALIZE_WITHIN
    exams = Exam.objects.filter(
        Q(course_id__in=course_ids) | Q(extensions__student_id=user.pk),
        status=Exam.Status.READY,
        opens_at__lte=now,
        closes_at__gte=recent,
    ).select_related("course")
    return list(exams.distinct().order_by("-opens_at"))


# --- Savollar ---


def question_pool(exam: Exam) -> list[int]:
    """Tanlangan modullar (bo'sh bo'lsa — kursning hammasi) dars testlarining savollari."""
    modules = list(exam.modules.values_list("pk", flat=True))
    quizzes = Quiz.objects.filter(lesson__module__course_id=exam.course_id)
    if modules:
        quizzes = quizzes.filter(lesson__module_id__in=modules)
    return list(Question.objects.filter(quiz__in=quizzes).values_list("pk", flat=True))


def current(attempt: ExamAttempt) -> tuple[int, int, Question] | None:
    """Birinchi javobsiz savol: (tartib raqami, jami, savol). Hammasi javoblangan — None."""
    questions = load_questions(attempt.question_ids)
    ids = [question_id for question_id in attempt.question_ids if question_id in questions]
    answered = set(attempt.answers.values_list("question_id", flat=True))
    for index, question_id in enumerate(ids, 1):
        if question_id not in answered:
            return index, len(ids), questions[question_id]
    return None


# --- Test qismi ---


def start_test(exam: Exam, user: User, *, now: datetime | None = None) -> ExamAttempt:
    """Testni boshlaydi yoki tugallanmaganini davom ettiradi (bitta urinish)."""
    now = now or timezone.now()
    existing = ExamAttempt.objects.filter(exam=exam, student=user).first()
    if existing is not None:
        if existing.finished_at is None and existing.deadline <= now:
            finish_test(existing, now=now)
        if existing.finished_at is not None:
            raise ExamError(_("Imtihon testini allaqachon topshirgansiz."))
        return existing
    if not available(exam, user, now=now):
        raise ExamError(_("Imtihon hozir ochiq emas."))
    pool = question_pool(exam)
    if not pool:
        raise ExamError(_("Imtihonda hali savol yo'q."))
    rng = random.SystemRandom()
    ids = rng.sample(pool, min(exam.questions_count, len(pool)))
    rng.shuffle(ids)
    deadline = min(now + timedelta(minutes=exam.duration_min), window_end(exam, user))
    try:
        with transaction.atomic():
            return ExamAttempt.objects.create(
                exam=exam,
                student=user,
                question_ids=ids,
                seed=rng.randrange(1, 2**31),
                deadline=deadline,
            )
    except IntegrityError:
        # Bir vaqtda ikki joydan (sayt va bot) bosilgan: bittasi yaratadi.
        return ExamAttempt.objects.get(exam=exam, student=user)


def seconds_left(attempt: ExamAttempt, *, now: datetime | None = None) -> int:
    if attempt.finished_at is not None:
        return 0
    return max(0, int((attempt.deadline - (now or timezone.now())).total_seconds()))


def answer_test(
    attempt: ExamAttempt,
    question_id: int,
    response: dict[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Javobni saqlaydi. To'g'ri yoki noto'g'riligi aytilmaydi (imtihon yopilgach)."""
    now = now or timezone.now()
    if attempt.finished_at is not None:
        raise ExamError(_("Imtihon testi yakunlangan."))
    if now >= attempt.deadline:
        finish_test(attempt, now=now)
        raise ExamError(_("Vaqt tugadi — berilgan javoblaringiz saqlandi."))
    if question_id not in attempt.question_ids:
        raise ExamError(_("Bu savol ushbu testda yo'q."))
    question = Question.objects.prefetch_related("choices").filter(pk=question_id).first()
    if question is None:
        raise ExamError(_("Savol topilmadi."))
    layout = Layout.build(question, attempt.seed)
    private = layout.to_private(response)
    if private is None:
        raise ExamError(_("Javob formati noto'g'ri."))
    try:
        with transaction.atomic():
            ExamAnswer.objects.create(
                attempt=attempt,
                question=question,
                response=private,
                correct=grading.grade(question, layout.choices, private),
            )
    except IntegrityError as exc:
        raise ExamError(_("Bu savolga javob berilgan.")) from exc
    return {"question": question.pk, "response": layout.to_public(private)}


def finish_test(attempt: ExamAttempt, *, now: datetime | None = None) -> ExamAttempt:
    """Test natijasi: javobsiz savollar noto'g'ri hisoblanadi."""
    now = now or timezone.now()
    with transaction.atomic():
        locked = ExamAttempt.objects.select_for_update().get(pk=attempt.pk)
        if locked.finished_at is None:
            total = Question.objects.filter(pk__in=locked.question_ids).count()
            correct = locked.answers.filter(correct=True).count()
            locked.score = round(correct * 100 / total) if total else 0
            locked.finished_at = min(now, locked.deadline)
            locked.save(update_fields=["score", "finished_at"])
    attempt.score, attempt.finished_at = locked.score, locked.finished_at
    exam = Exam.objects.get(pk=locked.exam_id)
    refresh_result(exam, User.objects.get(pk=locked.student_id), now=now)
    return locked


def review(attempt: ExamAttempt) -> list[dict[str, Any]]:
    """Imtihon yopilgach: har savol bo'yicha javob, to'g'ri javob va izoh."""
    questions = load_questions(attempt.question_ids)
    answers = {answer.question_id: answer for answer in attempt.answers.all()}
    return [
        result_payload(
            Layout.build(questions[question_id], attempt.seed),
            answers.get(question_id),  # type: ignore[arg-type]
            reveal=True,
        )
        for question_id in attempt.question_ids
        if question_id in questions
    ]


def attempt_payload(attempt: ExamAttempt, *, now: datetime | None = None) -> dict[str, Any]:
    """Brauzer uchun: savollar (javobsiz) va berilgan javoblar (natijasiz)."""
    now = now or timezone.now()
    questions = load_questions(attempt.question_ids)
    answers = {answer.question_id: answer for answer in attempt.answers.all()}
    items, done = [], []
    for question_id in attempt.question_ids:
        question = questions.get(question_id)
        if question is None:
            continue
        layout = Layout.build(question, attempt.seed)
        items.append(layout.payload())
        answer = answers.get(question_id)
        if answer is not None:
            done.append({"question": question_id, "response": layout.to_public(answer.response)})
    return {
        "id": attempt.pk,
        "exam_id": attempt.exam_id,
        "total": len(items),
        "deadline": attempt.deadline,
        "seconds_left": seconds_left(attempt, now=now),
        "finished": attempt.finished_at is not None,
        "score": attempt.score,
        "questions": items,
        "answers": done,
    }


# --- Amaliy topshiriqlar ---


def submit_task(
    task: ExamTask,
    user: User,
    *,
    text: str = "",
    code: str = "",
    language: str = "",
    link: str = "",
    files: Iterable[CheckedFile] = (),
    now: datetime | None = None,
) -> TaskAnswer:
    """Javob (yoki yangilash). Baholangan javobni o'zgartirib bo'lmaydi."""
    now = now or timezone.now()
    files = list(files)
    exam = task.exam
    if not available(exam, user, now=now):
        raise ExamError(_("Imtihon yopilgan — javob qabul qilinmaydi."))
    if not (text.strip() or code.strip() or link.strip() or files):
        raise ExamError(_("Javob bo'sh: izoh, kod, havola yoki fayl qo'shing."))
    with transaction.atomic():
        answer = TaskAnswer.objects.select_for_update().filter(task=task, student=user).first()
        if answer is not None and answer.score is not None:
            raise ExamError(_("Bu topshiriq baholangan — javobni o'zgartirib bo'lmaydi."))
        if answer is None:
            answer = TaskAnswer(task=task, student=user)
        else:
            for old in answer.files.all():
                old.file.delete(save=False)
                old.delete()
        answer.text = text.strip()
        answer.code = code.rstrip()
        answer.language = language.strip()[:20] if code.strip() else ""
        answer.link = link.strip()
        answer.save()
        for item in files:
            TaskAnswerFile.objects.create(
                answer=answer,
                file=item.upload,
                name=item.name,
                size=item.size,
                content_type=item.content_type,
                is_image=item.is_image,
            )
    refresh_result(exam, user, now=now)
    return answer


def grade_task(
    answer: TaskAnswer,
    reviewer: User,
    *,
    score: int,
    feedback: str = "",
    now: datetime | None = None,
) -> TaskAnswer:
    if not 0 <= score <= 100:
        raise ExamError(_("Baho 0 dan 100 gacha bo'lsin."))
    now = now or timezone.now()
    answer.score = score
    answer.feedback = feedback.strip()
    answer.reviewer = reviewer
    answer.reviewed_at = now
    answer.save(update_fields=["score", "feedback", "reviewer", "reviewed_at", "updated_at"])
    exam = answer.task.exam
    refresh_result(exam, answer.student, now=now)
    return answer


# --- Natija ---


@dataclass(frozen=True)
class Score:
    test: int
    practical: int
    total: int
    passed: bool


def compute(exam: Exam, student: Any) -> tuple[Score, bool, bool]:
    """Natija va holat: (ball, faollik bormi, baholanmagan yoki tugallanmagan narsa bormi)."""
    attempt = ExamAttempt.objects.filter(exam=exam, student_id=student.pk).first()
    tasks = list(exam.tasks.all())
    answers = {
        answer.task_id: answer
        for answer in TaskAnswer.objects.filter(task__exam=exam, student_id=student.pk)
    }
    active = attempt is not None or bool(answers)
    test = attempt.score if attempt is not None and attempt.score is not None else 0
    if tasks:
        scores = [(answers[task.pk].score or 0) if task.pk in answers else 0 for task in tasks]
        practical = round(sum(scores) / len(tasks))
        total = round((test * exam.test_weight + practical * (100 - exam.test_weight)) / 100)
    else:
        practical, total = 0, test
    pending = any(answer.score is None for answer in answers.values()) or (
        attempt is not None and attempt.finished_at is None
    )
    return Score(test, practical, total, total >= exam.pass_percent), active, pending


def refresh_result(exam: Exam, student: User, *, now: datetime | None = None) -> ExamResult | None:
    """Natijani qayta hisoblaydi. Imtihon yopilgan va hammasi baholangan bo'lsa — yakuniy:
    o'quvchiga xabar, sertifikat va XP hisobiga."""
    now = now or timezone.now()
    score, active, pending = compute(exam, student)
    if not active:
        return None
    result, _created = ExamResult.objects.update_or_create(
        exam=exam,
        student=student,
        defaults={
            "test_score": score.test,
            "practical_score": score.practical,
            "total": score.total,
            "passed": score.passed,
        },
    )
    if result.final_at is None and not pending and now >= window_end(exam, student):
        result.final_at = now
        result.save(update_fields=["final_at"])
        announce_result(result)
        events.exam_finalized.send(
            sender=ExamResult,
            user_id=student.pk,
            course_id=exam.course_id,
            exam_id=exam.pk,
            total=result.total,
            passed=result.passed,
        )
    return result


def announce_result(result: ExamResult) -> None:
    student = result.student
    exam = result.exam
    locale = locale_of(student.locale)
    with translation.override(locale):
        course = str(exam.course.title)
    status = text(locale, "exam_passed" if result.passed else "exam_failed")
    notify(
        student,
        Notification.Kind.EXAM_RESULT,
        title=text(locale, "exam_result_title", course=course),
        body=text(
            locale,
            "exam_result_body",
            total=str(result.total),
            status=status,
            test=str(result.test_score),
            practical=str(result.practical_score),
        ),
        link=f"/dashboard/exams/{exam.pk}",
        dedupe_key=f"exam-result:{exam.pk}:{student.pk}",
    )


# --- O'qituvchi ---


def teachers_for(course: Course) -> list[User]:
    """Kurs ustozlari va kurs guruhlari o'qituvchilari (faol)."""
    people = User.objects.filter(
        Q(instructor_profile__courses=course)
        | Q(
            teaching_groups__course=course,
            teaching_groups__status__in=[StudyGroup.Status.FORMING, StudyGroup.Status.ACTIVE],
        ),
        is_active=True,
    ).distinct()
    return list(people)


def can_manage(user: Any, exam: Exam) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if sees_all(user):
        return True
    return (
        teacher_courses(user).filter(pk=exam.course_id).exists()
        or StudyGroup.objects.filter(course_id=exam.course_id, teacher=user).exists()
    )


def students_of(viewer: Any, exam: Exam) -> list[User]:
    """O'qituvchi ko'radigan o'quvchilar: kurs ustozi va admin — hammasi, guruh o'qituvchisi —
    o'z guruhi. Imtihonda faollik ko'rsatgan (keyin kursdan chiqqan) o'quvchilar ham."""
    active_ids = set(
        ExamAttempt.objects.filter(exam=exam).values_list("student_id", flat=True)
    ) | set(TaskAnswer.objects.filter(task__exam=exam).values_list("student_id", flat=True))
    enrolled = set(participants(exam).order_by().values_list("pk", flat=True))
    people = User.objects.filter(pk__in=enrolled | active_ids)
    if not (sees_all(viewer) or teacher_courses(viewer).filter(pk=exam.course_id).exists()):
        own = Enrollment.objects.filter(course_id=exam.course_id, group__teacher=viewer).values(
            "user_id"
        )
        people = people.filter(pk__in=own)
    return list(people.distinct().order_by("first_name", "last_name", "pk"))


def grant_extension(
    exam: Exam, student: User, until: datetime, by: User, *, now: datetime | None = None
) -> ExamExtension:
    now = now or timezone.now()
    if until <= now:
        raise ExamError(_("Muddat kelajakda bo'lsin."))
    if until > exam.closes_at + FINALIZE_WITHIN:
        raise ExamError(_("Muddat imtihon yopilgandan keyin 45 kundan oshmasin."))
    extension, _created = ExamExtension.objects.update_or_create(
        exam=exam, student=student, defaults={"until": until, "granted_by": by}
    )
    return extension


# --- Jadval (Celery beat) ---


def covered_modules(course: Course, month: date) -> list[int]:
    """Shu oy guruhlarda o'tilgan ("Dars o'tildi") darslarning modullari."""
    start = timezone.make_aware(datetime.combine(month, time.min))
    end = timezone.make_aware(
        datetime.combine((month + timedelta(days=32)).replace(day=1), time.min)
    )
    return list(
        GroupLesson.objects.filter(group__course=course, opened_at__gte=start, opened_at__lt=end)
        .values_list("lesson__module_id", flat=True)
        .distinct()
    )


def create_drafts(*, today: date | None = None) -> int:
    """20-kuni: imtihon yoqilgan kurslarga shu oy imtihonining qoralamasi va ustozlarga eslatma."""
    today = today or timezone.localdate()
    month = month_start(today)
    opens, closes = window(month)
    created = 0
    for course in Course.objects.filter(monthly_exam=True, status=Course.Status.PUBLISHED):
        if Exam.objects.filter(course=course, month=month).exists():
            continue
        previous = Exam.objects.filter(course=course).order_by("-month").first()
        exam = Exam.objects.create(
            course=course,
            month=month,
            opens_at=opens,
            closes_at=closes,
            questions_count=previous.questions_count if previous else 20,
            duration_min=previous.duration_min if previous else 40,
            pass_percent=previous.pass_percent if previous else 60,
            test_weight=previous.test_weight if previous else 50,
        )
        exam.modules.set(covered_modules(course, month))
        created += 1
        for teacher in teachers_for(course):
            locale = locale_of(teacher.locale)
            with translation.override(locale):
                title = str(course.title)
            notify(
                teacher,
                Notification.Kind.EXAM_DRAFT,
                title=text(locale, "exam_draft_title", course=title),
                body=text(locale, "exam_draft_body", period=period(exam, locale)),
                link=f"/dashboard/teaching/exams/{exam.pk}",
                dedupe_key=f"exam-draft:{exam.pk}:{teacher.pk}",
            )
    return created


def announce_open(*, now: datetime | None = None) -> int:
    """Ochilgan imtihon — qatnashuvchilarga (kabinet va Telegram) bir marta."""
    now = now or timezone.now()
    sent = 0
    due = Exam.objects.filter(
        status=Exam.Status.READY,
        opens_at__lte=now,
        closes_at__gt=now,
        opened_notified_at__isnull=True,
    ).select_related("course")
    for exam in due:
        tasks = exam.tasks.count()
        for student in participants(exam, now=now):
            locale = locale_of(student.locale)
            with translation.override(locale):
                course = str(exam.course.title)
            created = notify(
                student,
                Notification.Kind.EXAM_OPENED,
                title=text(locale, "exam_opened_title", course=course),
                body=text(
                    locale,
                    "exam_opened_body",
                    period=period(exam, locale),
                    count=str(exam.questions_count),
                    minutes=str(exam.duration_min),
                    tasks=str(tasks),
                ),
                link=f"/dashboard/exams/{exam.pk}",
                dedupe_key=f"exam-open:{exam.pk}:{student.pk}",
            )
            sent += created is not None
        Exam.objects.filter(pk=exam.pk).update(opened_notified_at=now)
    return sent


def close_overdue(*, now: datetime | None = None) -> int:
    """Vaqti tugagan, lekin yakunlanmagan testlar (o'quvchi sahifani yopib ketgan)."""
    now = now or timezone.now()
    overdue = ExamAttempt.objects.filter(finished_at__isnull=True, deadline__lte=now)
    count = 0
    for attempt in overdue:
        finish_test(attempt, now=now)
        count += 1
    return count


def finalize(*, now: datetime | None = None) -> int:
    """Yopilgan imtihonlar natijalari: baholash tugagan o'quvchilarga yakuniy natija."""
    now = now or timezone.now()
    exams = Exam.objects.filter(closes_at__gte=now - FINALIZE_WITHIN, opens_at__lte=now)
    count = 0
    for exam in exams:
        students = set(
            ExamAttempt.objects.filter(exam=exam).values_list("student_id", flat=True)
        ) | set(TaskAnswer.objects.filter(task__exam=exam).values_list("student_id", flat=True))
        done = set(
            ExamResult.objects.filter(exam=exam, final_at__isnull=False).values_list(
                "student_id", flat=True
            )
        )
        for student in User.objects.filter(pk__in=students - done):
            result = refresh_result(exam, student, now=now)
            count += bool(result and result.final_at)
    return count


def pending_grading() -> QuerySet[TaskAnswer]:
    """Baholanmagan amaliy javoblar (admin muammolari uchun)."""
    return TaskAnswer.objects.filter(score__isnull=True)


def unready(
    *, now: datetime | None = None, within: timedelta = timedelta(days=5)
) -> QuerySet[Exam]:
    """Ochilishiga oz qolgan (yoki ochilishi kerak bo'lgan), lekin tayyor bo'lmagan imtihonlar."""
    now = now or timezone.now()
    return Exam.objects.filter(
        status=Exam.Status.DRAFT, opens_at__lte=now + within, closes_at__gt=now
    )


def groups_of(user_ids: Iterable[int], course_id: int) -> dict[int, str]:
    rows = Enrollment.objects.filter(
        user_id__in=list(user_ids), course_id=course_id, group__isnull=False
    ).values_list("user_id", "group__name")
    return dict(rows)
