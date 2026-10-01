"""Do'kon: olish (coin, zaxira, auditoriya), buyurtma holatlari va qaytarish, xabarlar, API."""

from typing import Any

import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from rest_framework.test import APIClient

from apps.notifications.models import Notification
from apps.rewards import services as rewards
from apps.rewards.models import Entry, Wallet
from apps.shop import services
from apps.shop.models import Product, Purchase
from apps.users.models import User
from apps.users.roles import Role, set_roles

pytestmark = pytest.mark.django_db
Status = Purchase.Status


def make_user(phone: str, *roles: str, audience: str = "ADULT") -> User:
    user = User.objects.create_user(phone=phone, password="x", first_name="Aziz", audience=audience)
    if roles:
        set_roles(user, roles)
    return user


def api(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture(autouse=True)
def _clean_cache() -> Any:
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def student() -> User:
    user = make_user("+998901000001", Role.STUDENT)
    rewards.credit(user.pk, Entry.Reason.MANUAL, key="seed", coins=100)
    return user


@pytest.fixture
def stickers() -> Product:
    return Product.objects.create(name_uz="Stikerlar", price=30, stock=2)


def coins(user: User) -> int:
    return Wallet.objects.get(user=user).coins


def test_buying_takes_coins_and_stock(student: User, stickers: Product) -> None:
    purchase = services.buy(student, stickers.pk)

    stickers.refresh_from_db()
    assert (purchase.status, purchase.price, purchase.name) == (Status.NEW, 30, "Stikerlar")
    assert (coins(student), stickers.stock) == (70, 1)
    entry = Entry.objects.get(reason=Entry.Reason.PURCHASE)
    assert (entry.coins, entry.note) == (-30, "Stikerlar")


def test_not_enough_coins_and_nothing_is_saved(student: User) -> None:
    shirt = Product.objects.create(name_uz="Futbolka", price=150)

    with pytest.raises(services.ShopError, match="yana 50 coin kerak"):
        services.buy(student, shirt.pk)

    assert not Purchase.objects.exists()
    assert coins(student) == 100


def test_sold_out_hidden_and_inactive(student: User, stickers: Product) -> None:
    Product.objects.filter(pk=stickers.pk).update(stock=0)
    with pytest.raises(services.ShopError, match="tugadi"):
        services.buy(student, stickers.pk)

    Product.objects.filter(pk=stickers.pk).update(stock=None, is_active=False)
    with pytest.raises(services.ShopError, match="sotuvda emas"):
        services.buy(student, stickers.pk)


def test_kids_gifts_are_only_for_kids(student: User) -> None:
    toy = Product.objects.create(name_uz="O'yinchoq", price=10, audience=Product.Audience.KIDS)

    with pytest.raises(services.ShopError, match="siz uchun emas"):
        services.buy(student, toy.pk)
    assert [item.pk for item in services.catalog(student)] == []

    kid = make_user("+998901000007", Role.STUDENT, audience="KIDS")
    rewards.credit(kid.pk, Entry.Reason.MANUAL, key="kid", coins=10)
    assert services.buy(kid, toy.pk).status == Status.NEW


def test_status_flow_refund_and_notifications(
    student: User, stickers: Product, django_capture_on_commit_callbacks: Any
) -> None:
    manager = make_user("+998901000005", Role.MANAGER)
    with django_capture_on_commit_callbacks(execute=True):
        purchase = services.buy(student, stickers.pk)
    assert Notification.objects.filter(user=manager, kind=Notification.Kind.SHOP).count() == 1

    with django_capture_on_commit_callbacks(execute=True):
        services.set_status(purchase, Status.READY, by=manager, note="Ertaga ofisdan oling")
    notice = Notification.objects.get(user=student, kind=Notification.Kind.SHOP)
    assert "Tayyor" in notice.title and "Ertaga ofisdan oling" in notice.body

    with django_capture_on_commit_callbacks(execute=True):
        services.set_status(purchase, Status.CANCELED, by=manager, note="Tugab qoldi")
    stickers.refresh_from_db()
    assert (coins(student), stickers.stock) == (100, 2)
    with pytest.raises(services.ShopError, match="bunday o'zgartirib"):
        services.set_status(purchase, Status.DELIVERED, by=manager)


def test_shop_api(student: User, stickers: Product) -> None:
    Product.objects.create(name_uz="Futbolka", price=150)
    client = api(student)

    shop = client.get("/api/v1/shop/").json()
    assert shop["coins"] == 100
    assert [(item["name"], item["affordable"]) for item in shop["products"]] == [
        ("Stikerlar", True),
        ("Futbolka", False),
    ]
    bought = client.post(f"/api/v1/shop/{stickers.pk}/buy/")
    assert bought.status_code == 201 and bought.json()["coins"] == 70
    [order] = client.get("/api/v1/shop/orders/").json()
    assert (order["name"], order["status"]) == ("Stikerlar", "NEW")
    failed = client.post(f"/api/v1/shop/{Product.objects.get(name_uz='Futbolka').pk}/buy/")
    assert failed.status_code == 400 and "coin kerak" in str(failed.json())


def test_admin_marks_delivered(student: User, stickers: Product) -> None:
    purchase = services.buy(student, stickers.pk)
    manager = make_user("+998901000005", Role.MANAGER)
    browser = Client()
    browser.force_login(manager)

    page = browser.get(reverse("admin:shop_purchase_change", args=[purchase.pk]))
    browser.post(
        reverse("admin:shop_purchase_mark_delivered", args=[purchase.pk]), HTTP_HX_REQUEST="true"
    )

    purchase.refresh_from_db()
    assert page.status_code == 200 and purchase.status == Status.DELIVERED
    # Maydonlar faqat o'qish uchun: "Saqlash" tugmasi yo'q, holat — amallar orqali.
    assert 'name="_save"' not in page.content.decode()
    assert purchase.handled_by == manager
