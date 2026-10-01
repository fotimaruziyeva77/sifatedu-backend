"""Referal: do'st birinchi darsni tugatsa va to'lasa — coin va kupon; do'stga chegirma."""

import pytest
from django.utils import timezone

from apps.catalog.models import Course
from apps.core import events
from apps.notifications.models import Notification
from apps.payments.models import Order
from apps.rewards import referral
from apps.rewards.models import Coupon, Entry, Wallet

from .conftest import World, api

pytestmark = pytest.mark.django_db


def other_course(world: World) -> Course:
    """Hali ochilmagan kurs (sotib olish uchun)."""
    return Course.objects.create(
        slug="backend",
        title_uz="Backend",
        category=world.course.category,
        status=Course.Status.PUBLISHED,
        price_online=1_000_000,
    )


def pay(order: Order) -> None:
    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.save(update_fields=["status", "paid_at"])
    events.order_paid.send(Order, order=order)


def test_friend_first_lesson_gives_coins_once(world: World) -> None:
    for lesson in world.lessons[:2]:
        events.lesson_completed.send(
            None, user_id=world.friend.pk, course_id=world.course.pk, lesson_id=lesson.pk
        )

    entry = Entry.objects.get(user=world.student, reason=Entry.Reason.REFERRAL)
    assert (entry.coins, entry.applied_xp, entry.note) == (50, 0, "Bekzod K.")
    assert Wallet.objects.get(user=world.student).coins == 50
    notice = Notification.objects.get(user=world.student, kind=Notification.Kind.REWARD)
    assert "Bekzod K." in notice.title and notice.link == "/dashboard/rewards"


def test_friend_gets_discount_on_the_first_order(world: World) -> None:
    course = other_course(world)
    response = api(world.friend).post(
        "/api/v1/orders/", {"course": course.slug, "study_format": "ONLINE"}, format="json"
    )

    assert response.status_code == 201
    order = Order.objects.get(user=world.friend)
    assert (order.full_amount, order.amount, order.discount_percent) == (1_000_000, 900_000, 10)
    assert order.discount_reason == "REFERRAL"
    assert api(world.friend).get("/api/v1/rewards/discount/").json() == {
        "discount": {"percent": 10, "reason": "REFERRAL"}
    }


def test_friend_payment_rewards_the_referrer_with_coins_and_a_coupon(world: World) -> None:
    first = Order.objects.create(
        user=world.friend, course=world.course, study_format="ONLINE", amount=900_000
    )
    pay(first)
    second = Order.objects.create(
        user=world.friend, course=world.course, study_format="ONLINE", amount=1_000_000
    )
    pay(second)

    assert Wallet.objects.get(user=world.student).coins == 100
    coupon = Coupon.objects.get(user=world.student)
    assert (coupon.percent, coupon.friend_id, coupon.used_at) == (10, world.friend.pk, None)
    assert referral.discount_for(world.friend) is None  # birinchi to'lov o'tdi


def test_coupon_is_applied_once(world: World) -> None:
    Coupon.objects.create(user=world.student, percent=10, friend=world.friend)
    client = api(world.student)
    course = other_course(world)

    client.post("/api/v1/orders/", {"course": course.slug, "study_format": "ONLINE"}, format="json")
    order = Order.objects.get(user=world.student)
    assert (order.amount, order.discount_reason) == (900_000, "COUPON")
    assert Coupon.objects.get().order_id == order.pk

    pay(order)
    assert Coupon.objects.get().used_at is not None
    assert client.get("/api/v1/rewards/discount/").json() == {"discount": None}
    assert api().get("/api/v1/rewards/discount/").json() == {"discount": None}


def test_no_discount_without_invitation(world: World) -> None:
    assert referral.discount_for(world.student) is None
    assert referral.discount_for(world.teacher) is None
