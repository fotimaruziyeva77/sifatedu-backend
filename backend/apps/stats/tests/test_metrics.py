"""Kunlik statistika: Toshkent vaqti bo'yicha kunlar, raqamlar, voronka, muammolar, xatolar."""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from apps.assistant.models import Conversation, Message
from apps.catalog.models import Category, Course
from apps.leads.models import Lead
from apps.learning.models import Enrollment
from apps.payments.models import Order
from apps.stats import metrics
from apps.stats.errors import ErrorCounter, error_counts
from apps.users.models import OneTimeCode, SocialAccount, User
from apps.users.roles import Role, set_roles
from apps.videos.models import VideoAsset

pytestmark = pytest.mark.django_db

TASHKENT = ZoneInfo("Asia/Tashkent")
NOW = datetime(2026, 9, 29, 12, 0, tzinfo=TASHKENT)


@pytest.fixture
def course(db: Any) -> Course:
    category = Category.objects.create(slug="it", name_uz="IT")
    return Course.objects.create(slug="frontend", title_uz="Frontend", category=category)


def joined(phone: str, when: datetime, **extra: Any) -> User:
    user = User.objects.create_user(phone=phone, password="x", **extra)
    User.objects.filter(pk=user.pk).update(date_joined=when)
    user.refresh_from_db()
    return user


def test_days_follow_tashkent_time() -> None:
    today = metrics.period("today", NOW)
    week = metrics.period("7d", NOW)

    # Toshkentda kun 00:00 da boshlanadi (UTC bo'yicha — oldingi kuni 19:00).
    assert today.start == datetime(2026, 9, 29, 0, 0, tzinfo=TASHKENT)
    assert today.previous.start == datetime(2026, 9, 28, 0, 0, tzinfo=TASHKENT)
    assert len(week.days) == 7 and week.days[-1] == NOW.date()
    assert metrics.period("nonsense", NOW).key == "today"


def test_summary_counts(course: Course) -> None:
    p = metrics.period("today")
    early = joined("+998901000001", p.start + timedelta(minutes=30))
    kid = joined("+998901000002", p.start + timedelta(hours=1), audience=User.Audience.KIDS)
    joined("+998901000003", p.start - timedelta(minutes=1))  # kecha
    joined("+998901000004", p.start, is_staff=True)  # xodim hisobga kirmaydi
    SocialAccount.objects.create(user=kid, provider=SocialAccount.Provider.TELEGRAM, uid="9")
    Enrollment.objects.create(user=early, course=course)
    Order.objects.filter(pk=Order.objects.create(user=kid, course=course, amount=300).pk).update(
        status=Order.Status.PAID, paid_at=p.start + timedelta(hours=2)
    )
    Lead.objects.create(name="A", phone="+998901111111")
    Lead.objects.create(name="B", phone="+998901111112", source=Lead.Source.AI_TELEGRAM)
    chat = Conversation.objects.create(user_messages=2)
    Message.objects.create(conversation=chat, role=Message.Role.ASSISTANT, cost_usd=Decimal("0.25"))

    summary = metrics.summary(p)

    assert (summary.registered, summary.kids, summary.via_telegram) == (2, 1, 1)
    assert (summary.chose_course, summary.enrolled, summary.started_payment) == (2, 1, 1)
    assert (summary.paid, summary.revenue) == (1, 300)
    assert (summary.leads, summary.leads_ai) == (2, 1)
    assert (summary.conversations, summary.ai_cost) == (1, Decimal("0.25"))
    assert metrics.summary(p.previous).registered == 1


def test_funnel_percentages(course: Course) -> None:
    p = metrics.period("today")
    users = [joined(f"+99890100002{index}", p.start) for index in range(4)]
    Enrollment.objects.create(user=users[0], course=course)
    Order.objects.create(user=users[0], course=course, amount=1, status=Order.Status.PAID)
    Order.objects.create(user=users[1], course=course, amount=1)

    steps = metrics.funnel(p)

    assert [(step.count, step.percent) for step in steps] == [(4, 100), (1, 25), (2, 50), (1, 25)]


def test_problems_and_links() -> None:
    now = timezone.now()
    p = metrics.period("today")
    old_lead = Lead.objects.create(name="A", phone="+998901111111")
    Lead.objects.filter(pk=old_lead.pk).update(created_at=now - timedelta(hours=3))
    Lead.objects.create(name="B", phone="+998901111112")  # hali yangi
    chat = Conversation.objects.create()
    Message.objects.create(conversation=chat, role=Message.Role.ASSISTANT, model="fallback")
    Message.objects.create(conversation=chat, role=Message.Role.ASSISTANT, model="rules")
    for index in range(3):
        OneTimeCode.objects.create(
            phone=f"+99890100003{index}",
            purpose=OneTimeCode.Purpose.REGISTER,
            code_hash="x",
            expires_at=now - timedelta(minutes=1),
        )
    VideoAsset.objects.create(title="Dars", status=VideoAsset.Status.FAILED)
    logging.getLogger("django.request").error("Internal Server Error: /api/")
    manager = User.objects.create_user(phone="+998909000001", password="x")
    set_roles(manager, [Role.MANAGER])

    found = {problem.title: problem for problem in metrics.problems(p, manager)}

    assert found["2 soatdan beri javobsiz arizalar"].count == 1
    assert found["AI javob bera olmadi (xato)"].level == "danger"
    assert found["AI Claude'siz, oddiy rejimda javob berdi"].count == 1
    assert found["SMS kod kiritilmadi"].level == "warning"
    assert found["Server xatolari (500)"].count == 1
    # Menejer videolarni ko'rmaydi — havola berilmaydi (403 bo'lardi).
    assert found["Video qayta ishlanmadi"].url == ""
    assert found["2 soatdan beri javobsiz arizalar"].url.endswith("?status__exact=NEW")
    assert next(iter(found.values())).level == "danger"


def test_no_problems_on_quiet_day() -> None:
    assert metrics.problems(metrics.period("today")) == []


def test_error_counter_groups_by_area() -> None:
    # Hisoblagich root logger'da (settings.LOGGING): har bir ERROR bo'limi bo'yicha sanaladi.
    assert any(isinstance(handler, ErrorCounter) for handler in logging.getLogger().handlers)
    logging.getLogger("apps.payments.click").error("Click javob bermadi")
    logging.getLogger("apps.payments.click").warning("ogohlantirish sanalmaydi")
    logging.getLogger("some.library").error("boshqa")

    counts = error_counts([timezone.localdate()])

    assert counts == {"payments": 1, "other": 1}


def test_call_list_without_course(course: Course) -> None:
    p = metrics.period("today")
    waiting = joined("+998901000041", timezone.now())
    enrolled = joined("+998901000042", timezone.now())
    Enrollment.objects.create(user=enrolled, course=course)

    people, total = metrics.without_course(p)

    assert people == [waiting] and total == 1
