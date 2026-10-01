"""Click SHOP API: imzo, summa, idempotentlik va kursning ochilishi."""

import hashlib
from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, Lesson, Module
from apps.learning.models import Enrollment
from apps.payments import click
from apps.payments.models import Order, PaymentLog, PaymentTransaction
from apps.users.models import User

pytestmark = pytest.mark.django_db

SERVICE_ID = "12345"
SECRET = "click-secret"
PREPARE_URL = "/api/v1/payments/click/prepare/"
COMPLETE_URL = "/api/v1/payments/click/complete/"


@pytest.fixture(autouse=True)
def click_settings(settings: Any) -> None:
    settings.CLICK_SERVICE_ID = SERVICE_ID
    settings.CLICK_MERCHANT_ID = "999"
    settings.CLICK_SECRET_KEY = SECRET


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def student(db: Any) -> User:
    return User.objects.create_user(phone="+998901112233", password="Parol12345")


@pytest.fixture
def course(db: Any) -> Course:
    category = Category.objects.create(slug="dasturlash", name_uz="Dasturlash")
    course = Course.objects.create(
        slug="frontend",
        title_uz="Frontend",
        category=category,
        status=Course.Status.PUBLISHED,
        study_format=Course.Format.BOTH,
        price_online=1_800_000,
        price_offline_monthly=700_000,
    )
    module = Module.objects.create(course=course, title_uz="Modul")
    Lesson.objects.create(module=module, title_uz="Dars", duration_min=20)
    return course


@pytest.fixture
def order(student: User, course: Course) -> Order:
    return Order.objects.create(
        user=student, course=course, study_format=Order.Format.ONLINE, amount=1_800_000
    )


def sign(parts: list[str]) -> str:
    return hashlib.md5("".join(parts).encode()).hexdigest()  # noqa: S324


def prepare_payload(order: Order, *, trans_id: str = "555", amount: str | None = None) -> dict:
    money = amount if amount is not None else f"{order.amount}.00"
    sign_time = "2026-09-27 10:00:00"
    return {
        "click_trans_id": trans_id,
        "service_id": SERVICE_ID,
        "click_paydoc_id": "777",
        "merchant_trans_id": str(order.pk),
        "amount": money,
        "action": "0",
        "error": "0",
        "error_note": "Success",
        "sign_time": sign_time,
        "sign_string": sign([trans_id, SERVICE_ID, SECRET, str(order.pk), money, "0", sign_time]),
    }


def complete_payload(
    order: Order,
    prepare_id: int,
    *,
    trans_id: str = "555",
    amount: str | None = None,
    error: str = "0",
) -> dict:
    money = amount if amount is not None else f"{order.amount}.00"
    sign_time = "2026-09-27 10:05:00"
    return {
        "click_trans_id": trans_id,
        "service_id": SERVICE_ID,
        "click_paydoc_id": "777",
        "merchant_trans_id": str(order.pk),
        "merchant_prepare_id": str(prepare_id),
        "amount": money,
        "action": "1",
        "error": error,
        "error_note": "Success",
        "sign_time": sign_time,
        "sign_string": sign(
            [
                trans_id,
                SERVICE_ID,
                SECRET,
                str(order.pk),
                str(prepare_id),
                money,
                "1",
                sign_time,
            ]
        ),
    }


def do_prepare(client: APIClient, order: Order, **kwargs: Any) -> dict:
    response = client.post(PREPARE_URL, prepare_payload(order, **kwargs), format="json")
    assert response.status_code == 200
    return dict(response.json())


def do_complete(client: APIClient, order: Order, prepare_id: int, **kwargs: Any) -> dict:
    response = client.post(
        COMPLETE_URL, complete_payload(order, prepare_id, **kwargs), format="json"
    )
    assert response.status_code == 200
    return dict(response.json())


class TestHappyPath:
    def test_prepare_then_complete_opens_course(
        self, client: APIClient, order: Order, student: User, course: Course
    ) -> None:
        prepared = do_prepare(client, order)

        assert prepared["error"] == click.OK
        assert PaymentTransaction.objects.get().status == PaymentTransaction.Status.PREPARED
        # Prepare kursni ochmaydi.
        assert not Enrollment.objects.exists()

        confirmed = do_complete(client, order, prepared["merchant_prepare_id"])

        assert confirmed["error"] == click.OK
        assert confirmed["merchant_confirm_id"] == prepared["merchant_prepare_id"]
        order.refresh_from_db()
        assert order.status == Order.Status.PAID
        assert order.paid_at is not None
        enrollment = Enrollment.objects.get(user=student, course=course)
        assert enrollment.source == Enrollment.Source.PAYMENT
        assert enrollment.study_format == Enrollment.Format.ONLINE
        # Onlayn — bir martalik to'lov: muddat yo'q.
        assert enrollment.expires_at is None

    def test_offline_payment_sets_expiry(
        self, client: APIClient, student: User, course: Course
    ) -> None:
        order = Order.objects.create(
            user=student,
            course=course,
            study_format=Order.Format.OFFLINE,
            months=3,
            amount=700_000 * 3,
        )
        prepared = do_prepare(client, order)
        do_complete(client, order, prepared["merchant_prepare_id"])

        enrollment = Enrollment.objects.get(user=student, course=course)
        assert enrollment.study_format == Enrollment.Format.OFFLINE
        assert enrollment.expires_at is not None
        # Uch oy: taxminan 89–93 kun.
        days = (enrollment.expires_at - timezone.now()).days
        assert 88 <= days <= 93

    def test_offline_renewal_extends_existing_period(
        self, client: APIClient, student: User, course: Course
    ) -> None:
        """Muddati tugamasdan to'lansa, yangi oy ustiga qo'shiladi."""
        first = Order.objects.create(
            user=student,
            course=course,
            study_format=Order.Format.OFFLINE,
            months=1,
            amount=700_000,
        )
        do_complete(client, first, do_prepare(client, first)["merchant_prepare_id"])
        after_first = Enrollment.objects.get(user=student, course=course).expires_at

        second = Order.objects.create(
            user=student,
            course=course,
            study_format=Order.Format.OFFLINE,
            months=1,
            amount=700_000,
        )
        do_complete(
            client,
            second,
            do_prepare(client, second, trans_id="556")["merchant_prepare_id"],
            trans_id="556",
        )

        after_second = Enrollment.objects.get(user=student, course=course).expires_at
        assert after_first is not None and after_second is not None
        assert (after_second - after_first).days >= 27

    def test_every_call_is_logged(self, client: APIClient, order: Order) -> None:
        prepared = do_prepare(client, order)
        do_complete(client, order, prepared["merchant_prepare_id"])

        actions = list(PaymentLog.objects.values_list("action", flat=True))
        assert sorted(actions) == ["complete", "prepare"]
        # Imzo logda saqlanmaydi.
        assert all("sign_string" not in log.request for log in PaymentLog.objects.all())


class TestSignature:
    def test_wrong_signature_is_rejected(self, client: APIClient, order: Order) -> None:
        payload = prepare_payload(order)
        payload["sign_string"] = "0" * 32

        result = client.post(PREPARE_URL, payload, format="json").json()

        assert result["error"] == click.SIGN_FAILED
        assert not PaymentTransaction.objects.exists()

    def test_missing_signature_is_rejected(self, client: APIClient, order: Order) -> None:
        payload = prepare_payload(order)
        payload["sign_string"] = ""

        assert client.post(PREPARE_URL, payload, format="json").json()["error"] == (
            click.SIGN_FAILED
        )

    def test_complete_signature_includes_prepare_id(self, client: APIClient, order: Order) -> None:
        """Complete imzosida `merchant_prepare_id` qatnashadi — Prepare imzosi o'tmaydi."""
        prepared = do_prepare(client, order)
        payload = complete_payload(order, prepared["merchant_prepare_id"])
        sign_time = payload["sign_time"]
        payload["sign_string"] = sign(
            ["555", SERVICE_ID, SECRET, str(order.pk), payload["amount"], "1", sign_time]
        )

        assert client.post(COMPLETE_URL, payload, format="json").json()["error"] == (
            click.SIGN_FAILED
        )
        order.refresh_from_db()
        assert order.status == Order.Status.NEW


class TestAmount:
    def test_wrong_amount_is_rejected(self, client: APIClient, order: Order) -> None:
        result = client.post(
            PREPARE_URL, prepare_payload(order, amount="1000.00"), format="json"
        ).json()

        assert result["error"] == click.BAD_AMOUNT
        assert not PaymentTransaction.objects.exists()

    def test_decimal_amount_matches(self, client: APIClient, order: Order) -> None:
        """Click summani "1800000.00" ko'rinishida yuboradi."""
        assert do_prepare(client, order, amount="1800000.00")["error"] == click.OK

    def test_amount_checked_again_on_complete(self, client: APIClient, order: Order) -> None:
        prepared = do_prepare(client, order)

        result = client.post(
            COMPLETE_URL,
            complete_payload(order, prepared["merchant_prepare_id"], amount="1.00"),
            format="json",
        ).json()

        assert result["error"] == click.BAD_AMOUNT
        order.refresh_from_db()
        assert order.status == Order.Status.NEW


class TestIdempotency:
    def test_complete_twice_does_not_double_charge(self, client: APIClient, order: Order) -> None:
        prepared = do_prepare(client, order)
        do_complete(client, order, prepared["merchant_prepare_id"])

        again = do_complete(client, order, prepared["merchant_prepare_id"])

        assert again["error"] == click.ALREADY_PAID
        assert Enrollment.objects.count() == 1
        assert PaymentTransaction.objects.count() == 1

    def test_prepare_twice_returns_same_transaction(self, client: APIClient, order: Order) -> None:
        first = do_prepare(client, order)
        second = do_prepare(client, order)

        assert first["merchant_prepare_id"] == second["merchant_prepare_id"]
        assert PaymentTransaction.objects.count() == 1

    def test_prepare_after_payment_is_rejected(self, client: APIClient, order: Order) -> None:
        prepared = do_prepare(client, order)
        do_complete(client, order, prepared["merchant_prepare_id"])

        result = client.post(
            PREPARE_URL, prepare_payload(order, trans_id="999"), format="json"
        ).json()

        assert result["error"] == click.ALREADY_PAID


class TestBadRequests:
    def test_complete_without_prepare(self, client: APIClient, order: Order) -> None:
        result = client.post(COMPLETE_URL, complete_payload(order, 1), format="json").json()

        assert result["error"] == click.TRANSACTION_NOT_FOUND
        order.refresh_from_db()
        assert order.status == Order.Status.NEW

    def test_unknown_order(self, client: APIClient, order: Order) -> None:
        missing = Order(pk=order.pk + 1000, amount=order.amount)

        result = client.post(PREPARE_URL, prepare_payload(missing), format="json").json()

        assert result["error"] == click.ORDER_NOT_FOUND

    def test_expired_order_cannot_be_paid(self, client: APIClient, order: Order) -> None:
        Order.objects.filter(pk=order.pk).update(status=Order.Status.EXPIRED)

        result = client.post(PREPARE_URL, prepare_payload(order), format="json").json()

        assert result["error"] == click.ORDER_CLOSED
        assert not Enrollment.objects.exists()

    def test_click_error_cancels_transaction(self, client: APIClient, order: Order) -> None:
        """Click o'zi xato bilan kelsa, kurs ochilmaydi."""
        prepared = do_prepare(client, order)

        result = do_complete(client, order, prepared["merchant_prepare_id"], error="-5001")

        assert result["error"] == click.ORDER_CLOSED
        assert PaymentTransaction.objects.get().status == PaymentTransaction.Status.CANCELLED
        order.refresh_from_db()
        assert order.status == Order.Status.NEW
        assert not Enrollment.objects.exists()

    def test_wrong_action_is_rejected(self, client: APIClient, order: Order) -> None:
        payload = prepare_payload(order)
        payload["action"] = "7"

        result = client.post(PREPARE_URL, payload, format="json").json()

        assert result["error"] in (click.ACTION_NOT_FOUND, click.SIGN_FAILED)

    def test_prepare_endpoint_rejects_complete_action(
        self, client: APIClient, order: Order
    ) -> None:
        prepared = do_prepare(client, order)
        payload = complete_payload(order, prepared["merchant_prepare_id"])

        result = client.post(PREPARE_URL, payload, format="json").json()

        assert result["error"] == click.ACTION_NOT_FOUND
