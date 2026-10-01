"""Buyurtma: summa serverda, cheklovlar va muddati o'tishi."""

from datetime import timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course
from apps.learning.models import Enrollment
from apps.payments.models import Order
from apps.payments.pricing import add_months
from apps.payments.tasks import expire_orders
from apps.users.models import User

pytestmark = pytest.mark.django_db

URL = "/api/v1/orders/"


@pytest.fixture(autouse=True)
def click_settings(settings: Any) -> None:
    settings.CLICK_SERVICE_ID = "12345"
    settings.CLICK_MERCHANT_ID = "999"
    settings.CLICK_SECRET_KEY = "click-secret"


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def student(db: Any) -> User:
    return User.objects.create_user(phone="+998901112233", password="Parol12345")


@pytest.fixture
def course(db: Any) -> Course:
    category = Category.objects.create(slug="dasturlash", name_uz="Dasturlash")
    return Course.objects.create(
        slug="frontend",
        title_uz="Frontend",
        category=category,
        status=Course.Status.PUBLISHED,
        study_format=Course.Format.BOTH,
        price_online=1_800_000,
        price_offline_monthly=700_000,
    )


def create(client: APIClient, **body: Any) -> Any:
    return client.post(URL, {"course": "frontend", **body}, format="json")


class TestCreate:
    def test_requires_login(self, client: APIClient, course: Course) -> None:
        assert create(client, study_format="ONLINE").status_code == 403

    def test_amount_is_calculated_on_server(
        self, client: APIClient, student: User, course: Course
    ) -> None:
        client.force_authenticate(student)

        # Client 1 so'm yuborsa ham, summa kursdan olinadi.
        response = create(client, study_format="ONLINE", amount=1)

        assert response.status_code == 201
        data = response.json()
        assert data["order"]["amount"] == 1_800_000
        assert Order.objects.get().amount == 1_800_000
        assert data["pay_url"].startswith("https://my.click.uz/services/pay?")
        assert f"transaction_param={Order.objects.get().pk}" in data["pay_url"]

    def test_return_url_keeps_language(
        self, client: APIClient, student: User, course: Course
    ) -> None:
        client.force_authenticate(student)

        response = client.post(
            URL,
            {"course": "frontend", "study_format": "ONLINE"},
            format="json",
            HTTP_ACCEPT_LANGUAGE="ru",
        )

        query = parse_qs(urlparse(response.json()["pay_url"]).query)
        order_id = Order.objects.get().pk
        assert query["return_url"] == [f"http://localhost/ru/payment/result?order={order_id}"]

    def test_offline_amount_multiplies_by_months(
        self, client: APIClient, student: User, course: Course
    ) -> None:
        client.force_authenticate(student)

        response = create(client, study_format="OFFLINE", months=4)

        assert response.json()["order"]["amount"] == 700_000 * 4

    def test_online_ignores_months(self, client: APIClient, student: User, course: Course) -> None:
        client.force_authenticate(student)

        data = create(client, study_format="ONLINE", months=6).json()["order"]

        assert (data["amount"], data["months"]) == (1_800_000, 1)

    def test_too_many_months_is_rejected(
        self, client: APIClient, student: User, course: Course
    ) -> None:
        client.force_authenticate(student)

        assert create(client, study_format="OFFLINE", months=13).status_code == 400

    def test_free_course_cannot_be_bought(
        self, client: APIClient, student: User, course: Course
    ) -> None:
        Course.objects.filter(pk=course.pk).update(is_free=True)
        client.force_authenticate(student)

        response = create(client, study_format="ONLINE")

        assert response.status_code == 400
        assert not Order.objects.exists()

    def test_unpublished_course_cannot_be_bought(
        self, client: APIClient, student: User, course: Course
    ) -> None:
        Course.objects.filter(pk=course.pk).update(status=Course.Status.DRAFT)
        client.force_authenticate(student)

        assert create(client, study_format="ONLINE").status_code == 400

    def test_format_must_match_course(
        self, client: APIClient, student: User, course: Course
    ) -> None:
        Course.objects.filter(pk=course.pk).update(study_format=Course.Format.ONLINE)
        client.force_authenticate(student)

        assert create(client, study_format="OFFLINE").status_code == 400
        assert create(client, study_format="ONLINE").status_code == 201

    def test_price_not_set_is_rejected(
        self, client: APIClient, student: User, course: Course
    ) -> None:
        Course.objects.filter(pk=course.pk).update(price_online=0)
        client.force_authenticate(student)

        assert create(client, study_format="ONLINE").status_code == 400

    def test_already_open_course_cannot_be_bought_again(
        self, client: APIClient, student: User, course: Course
    ) -> None:
        Enrollment.objects.create(user=student, course=course, source=Enrollment.Source.PAYMENT)
        client.force_authenticate(student)

        assert create(client, study_format="ONLINE").status_code == 400

    def test_offline_subscription_can_be_renewed(
        self, client: APIClient, student: User, course: Course
    ) -> None:
        Enrollment.objects.create(
            user=student,
            course=course,
            study_format=Enrollment.Format.OFFLINE,
            expires_at=timezone.now() + timedelta(days=5),
        )
        client.force_authenticate(student)

        assert create(client, study_format="OFFLINE", months=1).status_code == 201


class TestList:
    def test_only_my_orders(self, client: APIClient, student: User, course: Course) -> None:
        other = User.objects.create_user(phone="+998907776655", password="Parol12345")
        Order.objects.create(user=other, course=course, amount=100)
        mine = Order.objects.create(user=student, course=course, amount=200)
        client.force_authenticate(student)

        data = client.get(URL).json()

        assert [item["id"] for item in data] == [mine.pk]

    def test_detail_of_other_user_is_hidden(
        self, client: APIClient, student: User, course: Course
    ) -> None:
        other = User.objects.create_user(phone="+998907776655", password="Parol12345")
        order = Order.objects.create(user=other, course=course, amount=100)
        client.force_authenticate(student)

        assert client.get(f"{URL}{order.pk}/").status_code == 404


class TestExpiry:
    def test_unpaid_order_expires_after_thirty_minutes(self, student: User, course: Course) -> None:
        fresh = Order.objects.create(user=student, course=course, amount=100)
        stale = Order.objects.create(user=student, course=course, amount=100)
        Order.objects.filter(pk=stale.pk).update(created_at=timezone.now() - timedelta(minutes=31))

        expire_orders()

        fresh.refresh_from_db()
        stale.refresh_from_db()
        assert fresh.status == Order.Status.NEW
        assert stale.status == Order.Status.EXPIRED

    def test_paid_order_is_not_expired(self, student: User, course: Course) -> None:
        order = Order.objects.create(
            user=student, course=course, amount=100, status=Order.Status.PAID
        )
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(days=2))

        expire_orders()

        order.refresh_from_db()
        assert order.status == Order.Status.PAID


class TestAddMonths:
    @pytest.mark.parametrize(
        ("start", "months", "expected"),
        [
            ((2026, 1, 15), 1, (2026, 2, 15)),
            ((2026, 1, 31), 1, (2026, 2, 28)),
            ((2024, 1, 31), 1, (2024, 2, 29)),  # kabisa yili
            ((2026, 11, 30), 2, (2027, 1, 30)),
            ((2026, 12, 31), 1, (2027, 1, 31)),
            ((2026, 3, 15), 12, (2027, 3, 15)),
        ],
    )
    def test_calendar_months(
        self, start: tuple[int, int, int], months: int, expected: tuple[int, int, int]
    ) -> None:
        from datetime import date

        assert add_months(date(*start), months) == date(*expected)
