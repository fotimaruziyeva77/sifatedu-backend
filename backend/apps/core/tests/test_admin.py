"""Admin'da ro'yxatdan o'tgan har bir model sahifalari xatosiz ochiladi."""

import io
from datetime import time, timedelta
from typing import Any

import pytest
from django.contrib import admin
from django.core.management import call_command
from django.db.models import Model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.assistant.models import AssistantSettings, Conversation, Message
from apps.bot.models import BotChat, RequiredChannel
from apps.catalog.models import Course, Instructor, Lesson
from apps.certificates.models import Certificate
from apps.content import models as content_models
from apps.dailytest.models import DailyAnswer, DailyAttempt, DailyTest
from apps.exams.models import Exam, ExamResult, ExamTask
from apps.homework.models import Assignment, Submission
from apps.leads.models import Lead
from apps.learning.models import Enrollment, LessonProgress, StudyGroup
from apps.live.models import Attendance, LiveLesson, ScheduleSlot
from apps.notifications.models import Broadcast, Notification
from apps.payments.models import Order, PaymentLog, PaymentTransaction, Refund
from apps.placement.models import PlacementAnswer, PlacementAttempt, PlacementTest
from apps.quizzes.models import Answer, Attempt, Choice, Question, Quiz
from apps.rewards.models import Coupon, DailyTask, Entry, GameSettings, Wallet
from apps.shop.models import Product, Purchase
from apps.users.models import OneTimeCode, User
from apps.videos.models import VideoAsset

MODELS = sorted(admin.site._registry, key=lambda model: model._meta.label)


def admin_url(model: type[Model], view: str, *args: Any) -> str:
    meta = model._meta
    return reverse(f"admin:{meta.app_label}_{meta.model_name}_{view}", args=args)


@pytest.fixture
def staff_client(db: Any) -> Client:
    # Namunaviy kontent + seed yaratmaydigan modellar: har bir modelda kamida bitta obyekt bo'ladi.
    call_command("seed_demo", stdout=io.StringIO())
    content_models.Testimonial.objects.create(author_name="Ali Valiyev", text_uz="Zo'r kurs")
    Lead.objects.create(name="Ali", phone="+998901112233")
    OneTimeCode.objects.create(
        phone="+998901112233", purpose="register", code_hash="x" * 64, expires_at=timezone.now()
    )
    Instructor.objects.create(slug="ustoz", full_name="Ustoz", position_uz="Mentor")
    VideoAsset.objects.create(title="Namunaviy video", status=VideoAsset.Status.READY)
    student = User.objects.create_user(phone="+998901234567", password="Str0ng-pass")
    course = Course.objects.first()
    lesson = Lesson.objects.first()
    assert course is not None and lesson is not None, "seed_demo katalogni to'ldirmadi"
    teacher = User.objects.create_user(phone="+998901234568", password="Str0ng-pass")
    group = StudyGroup.objects.create(course=course, teacher=teacher, name="FE-1")
    Enrollment.objects.create(user=student, course=course, group=group)
    LessonProgress.objects.create(user=student, lesson=lesson, position_sec=30)
    order = Order.objects.create(user=student, course=course, amount=100_000)
    PaymentTransaction.objects.create(order=order, provider_trans_id="1", amount=order.amount)
    PaymentLog.objects.create(action="prepare", order=order, request={}, response={"error": 0})
    Refund.objects.create(order=order, amount=order.amount, reason="Sinov")
    AssistantSettings.load()
    conversation = Conversation.objects.create(name="Aziz", lead=Lead.objects.first())
    Message.objects.create(conversation=conversation, role=Message.Role.USER, text="Salom")
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        text="Assalomu alaykum",
        content=[{"type": "tool_use", "id": "t1", "name": "get_course", "input": {"slug": "x"}}],
        rating=Message.Rating.BAD,
    )
    assignment = Assignment.objects.create(lesson=lesson, instructions="Sahifa yasang")
    Submission.objects.create(assignment=assignment, student=student, text="Tayyor", code="<p>")
    quiz = Quiz.objects.create(lesson=lesson, title="HTML asoslari")
    question = Question.objects.create(quiz=quiz, text="HTML nima?")
    Choice.objects.create(question=question, text="Belgilash tili", is_correct=True)
    Choice.objects.create(question=question, text="Dasturlash tili")
    attempt = Attempt.objects.create(
        quiz=quiz, student=student, question_ids=[question.pk], score=100, stars=3, passed=True
    )
    Answer.objects.create(attempt=attempt, question=question, response={"choice": 1}, correct=True)
    placement = PlacementTest.objects.create(course=course, title="Python", quiz=quiz)
    tried = PlacementAttempt.objects.create(
        test=placement, user=student, question_ids=[question.pk], deadline=timezone.now(), score=100
    )
    PlacementAnswer.objects.create(attempt=tried, question=question, correct=True)
    ScheduleSlot.objects.create(group=group, weekday=0, starts_at=time(18, 0))
    today = DailyTest.objects.create(
        group=group,
        day=timezone.localdate(),
        opens_at=timezone.now(),
        closes_at=timezone.now() + timedelta(hours=8),
    )
    daily = DailyAttempt.objects.create(
        test=today, student=student, question_ids=[question.pk], correct=1, total=1
    )
    DailyAnswer.objects.create(attempt=daily, question=question, correct=True)
    live = LiveLesson.objects.create(
        group=group,
        starts_at=timezone.now() + timedelta(days=1),
        meet_url="https://meet.google.com/abc-defg-hij",
    )
    Attendance.objects.create(live_lesson=live, student=student, status="PRESENT")
    broadcast = Broadcast.objects.create(title="Ertaga dars yo'q", body="Dam oling")
    broadcast.courses.add(course)
    Notification.objects.create(
        user=student, kind=Notification.Kind.BROADCAST, broadcast=broadcast, title="Ertaga"
    )
    BotChat.objects.create(chat_id=4242, first_name="Aziz", username="aziz", language="uz")
    RequiredChannel.objects.create(title="Sifat Edu", chat="@sifatedu", url="https://t.me/sifatedu")
    now = timezone.now()
    exam = Exam.objects.create(
        course=course,
        month=now.date().replace(day=1),
        opens_at=now - timedelta(days=1),
        closes_at=now + timedelta(days=5),
    )
    ExamTask.objects.create(exam=exam, order=1, title="Sahifa", instructions="Yarating")
    ExamResult.objects.create(exam=exam, student=student, test_score=80, total=80, passed=True)
    Certificate.objects.create(
        user=student, course=course, number="SE-2610-ABCDEF", full_name="Aziz Valiyev", score=90
    )
    GameSettings.objects.get_or_create(pk=1)
    Wallet.objects.create(user=student, xp=10, coins=10)
    Entry.objects.create(user=student, reason=Entry.Reason.LESSON, xp=10, coins=10, key="smoke")
    DailyTask.objects.create(user=student, kind=DailyTask.Kind.LESSON, title="Dars")
    Coupon.objects.create(user=student, percent=10)
    gift = Product.objects.create(name_uz="Stikerlar", price=30, stock=5)
    Purchase.objects.create(user=student, product=gift, name="Stikerlar", price=30)
    user = User.objects.create_superuser(phone="+998900000009", password="Str0ng-pass")
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.parametrize("model", MODELS, ids=lambda model: model._meta.label)
def test_changelist_with_search(staff_client: Client, model: type[Model]) -> None:
    response = staff_client.get(admin_url(model, "changelist"), {"q": "a"}, follow=True)

    assert response.status_code == 200


@pytest.mark.parametrize("model", MODELS, ids=lambda model: model._meta.label)
def test_add_view(staff_client: Client, model: type[Model]) -> None:
    response = staff_client.get(admin_url(model, "add"))

    can_add = admin.site._registry[model].has_add_permission(response.wsgi_request)
    assert response.status_code == (200 if can_add else 403)


@pytest.mark.parametrize("model", MODELS, ids=lambda model: model._meta.label)
def test_change_view(staff_client: Client, model: type[Model]) -> None:
    obj = model._default_manager.first()
    assert obj is not None

    response = staff_client.get(admin_url(model, "change", obj.pk))

    assert response.status_code == 200
