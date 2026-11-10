"""Markaz sozlamalari: kalitlar shifrlangan va markazlar orasida aralashmaydi, brend, SMS limiti."""

from collections.abc import Iterator
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from django.apps import apps as django_apps
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection as db_connection
from django.test import override_settings
from django_tenants.utils import get_public_schema_name, schema_context
from PIL import Image
from rest_framework.test import APIClient

from apps.assistant.budget import monthly_limit
from apps.assistant.models import AssistantSettings
from apps.assistant.prompt import build_system_prompt
from apps.content.models import SiteSettings
from apps.integrations import conf
from apps.integrations.fields import seal, unseal
from apps.integrations.models import Integrations
from apps.integrations.testing import set_keys
from apps.notifications import alerts, sms
from apps.notifications import tasks as notification_tasks
from apps.notifications import telegram as telegram_api
from apps.tenancy.db import connection
from apps.tenancy.limits import LimitReached, check_disk
from apps.tenancy.models import Center, Plan
from apps.tenancy.sites import center_name, is_flagship, rebrand, site_url
from apps.users import otp
from apps.users import services as user_services
from apps.users.models import User
from apps.users.roles import Role, set_roles

from .conftest import SECOND_HOST

pytestmark = pytest.mark.django_db

SETUP = "/api/v1/center/setup/"
TOKEN = "123456:SIRLI-TOKEN"
INFO = "/api/v1/center/"

import_env = __import__(
    "apps.integrations.migrations.0002_import_env", fromlist=["import_env"]
).import_env


@pytest.fixture(autouse=True)
def _clean() -> None:
    cache.clear()


@pytest.fixture
def admin_client() -> APIClient:
    user = User.objects.create_user(phone="+998900000100", password="x")
    set_roles(user, [Role.ADMIN])
    client = APIClient()
    client.force_authenticate(user)
    return client


def use_plan(**changes: Any) -> Plan:
    plan = Plan.objects.get(name="Pro")
    for name, value in changes.items():
        setattr(plan, name, value)
    plan.save()
    Center.objects.filter(schema_name=connection.schema_name).update(plan=plan)
    connection.tenant.__dict__.pop("plan", None)
    connection.set_tenant(
        Center.objects.select_related("plan").get(schema_name=connection.schema_name)
    )
    return plan


def logo_file(name: str = "logo.png", image_format: str = "PNG") -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", (8, 8)).save(buffer, image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


# --- Kalitlar ---


def test_secrets_are_encrypted_at_rest() -> None:
    set_keys(telegram_token=TOKEN, click_secret_key="click-sir", eskiz_password="parol-sir")

    with db_connection.cursor() as cursor:
        cursor.execute(
            "SELECT telegram_token, click_secret_key, eskiz_password FROM integrations_integrations"
        )
        raw = cursor.fetchone()

    assert TOKEN not in raw[0] and "click-sir" not in raw[1] and "parol-sir" not in raw[2]
    assert conf.telegram().token == TOKEN
    assert conf.click().secret_key == "click-sir"
    assert conf.eskiz().password == "parol-sir"


def test_changed_secrets_read_as_not_configured() -> None:
    token = seal("qiymat")
    with override_settings(INTEGRATIONS_SECRET="boshqa-sir", SECRET_KEY="boshqa-kalit"):
        assert unseal(token) == ""


def test_secret_added_later_keeps_old_values_readable() -> None:
    old = seal("qiymat")
    with override_settings(INTEGRATIONS_SECRET="keyin-qo'shilgan-sir"):
        assert unseal(old) == "qiymat"
        new = seal("yangi")
        assert unseal(new) == "yangi"
    assert unseal(new) == ""


def test_centers_do_not_share_keys(second_center: Center) -> None:
    set_keys(telegram_token=TOKEN, telegram_username="birinchi_bot", click_service_id="1")

    with schema_context(second_center.schema_name):
        assert conf.telegram().token == ""
        assert conf.click().service_id == ""


def test_platform_uses_env_keys(settings: Any) -> None:
    settings.TELEGRAM_BOT_TOKEN = "platforma-tokeni"
    settings.ESKIZ_EMAIL = "platform@b.uz"

    with schema_context(get_public_schema_name()):
        assert conf.telegram().token == "platforma-tokeni"
        assert conf.eskiz().email == "platform@b.uz"


def test_first_center_keys_are_imported_from_env(settings: Any) -> None:
    settings.TELEGRAM_BOT_TOKEN = TOKEN
    settings.TELEGRAM_BOT_USERNAME = "@sifat_bot"
    settings.TELEGRAM_WEBHOOK_SECRET = "webhook"
    settings.CLICK_SECRET_KEY = "click-sir"
    settings.ESKIZ_PASSWORD = "parol"

    editor = SimpleNamespace(connection=SimpleNamespace(schema_name=settings.FIRST_CENTER_SCHEMA))
    import_env(django_apps, editor)

    row = Integrations.load()
    assert row.telegram_token == TOKEN
    assert row.telegram_username == "sifat_bot"
    assert row.telegram_webhook_secret == "webhook"
    assert row.telegram_login is True
    assert row.click_secret_key == "click-sir"
    assert row.eskiz_password == "parol"


def test_other_centers_do_not_import_env(settings: Any) -> None:
    settings.TELEGRAM_BOT_TOKEN = TOKEN

    editor = SimpleNamespace(connection=SimpleNamespace(schema_name="boshqa"))
    import_env(django_apps, editor)

    assert conf.telegram().token == ""


# --- Manzil va nom ---


def test_site_url_is_the_centers_own(second_center: Center, settings: Any) -> None:
    settings.SITE_SCHEME = "https"

    assert site_url() == "https://testserver"
    with schema_context(second_center.schema_name):
        assert site_url() == f"https://{SECOND_HOST}"


def test_texts_use_center_name(second_center: Center) -> None:
    text = "Sifat Edu botiga xush kelibsiz! SIFAT Kids"

    assert is_flagship()
    assert rebrand(text) == text
    with schema_context(second_center.schema_name):
        assert not is_flagship()
        assert center_name() == "Ikkinchi markaz"
        assert rebrand(text) == "Ikkinchi markaz botiga xush kelibsiz! Kids"


def test_ai_prompt_drops_flagship_specifics(second_center: Center) -> None:
    with schema_context(second_center.schema_name):
        prompt = build_system_prompt("uz")

    assert "Sifat Edu" not in prompt
    assert "SIFAT Kids" not in prompt
    assert "IT kasblari" not in prompt
    assert "«Ikkinchi markaz»" in prompt


def test_center_info_on_platform_address() -> None:
    body = APIClient().get(INFO, HTTP_HOST="platform.testserver").json()

    assert body["kind"] == "platform"
    assert body["name"] == "Test platforma"
    assert body["base_domain"] == "testserver"


def test_unknown_address_is_404() -> None:
    assert APIClient().get(INFO, HTTP_HOST="yoq.testserver").status_code == 404


# --- Sozlamalar API ---


def test_settings_are_for_admins_only() -> None:
    user = User.objects.create_user(phone="+998900000101", password="x")
    set_roles(user, [Role.MANAGER])
    client = APIClient()
    client.force_authenticate(user)

    assert client.get(SETUP).status_code == 403
    assert APIClient().get(SETUP).status_code in (401, 403)


def test_setup_never_returns_secrets(admin_client: APIClient) -> None:
    set_keys(
        telegram_token=TOKEN,
        telegram_webhook_secret="webhook-sir",
        click_service_id="1",
        click_secret_key="click-sir",
        eskiz_email="a@b.uz",
        eskiz_password="parol-sir",
    )

    response = admin_client.get(SETUP)

    assert response.status_code == 200
    text = response.content.decode()
    for secret in (TOKEN, "webhook-sir", "click-sir", "parol-sir"):
        assert secret not in text
    body = response.json()
    assert body["telegram"]["connected"] is True
    assert body["click"]["connected"] is True
    assert body["eskiz"]["connected"] is True
    assert body["click"]["prepare_url"].endswith("/api/v1/payments/click/prepare/")


def test_connect_bot_checks_token_and_sets_webhook(admin_client: APIClient, settings: Any) -> None:
    settings.SITE_SCHEME = "https"
    calls: list[tuple[str, dict[str, Any], str | None]] = []

    def fake(method: str, payload: dict[str, Any], *, token: str | None = None, **_: Any) -> Any:
        calls.append((method, payload, token))
        return {"username": "yangi_bot"} if method == "getMe" else True

    with patch.object(telegram_api, "call", side_effect=fake):
        response = admin_client.put("/api/v1/center/telegram/", {"token": TOKEN}, format="json")

    assert response.status_code == 200
    assert TOKEN not in response.content.decode()
    row = Integrations.load()
    assert (row.telegram_token, row.telegram_username) == (TOKEN, "yangi_bot")
    assert row.telegram_webhook_secret
    methods = [call[0] for call in calls]
    assert methods[:2] == ["getMe", "setWebhook"]
    assert "setMyCommands" in methods
    webhook = next(call[1] for call in calls if call[0] == "setWebhook")
    assert webhook["url"] == "https://testserver/api/v1/bot/webhook/"
    assert webhook["secret_token"] == row.telegram_webhook_secret
    assert all(call[2] == TOKEN for call in calls)


def test_wrong_bot_token_is_not_saved(admin_client: APIClient) -> None:
    with patch.object(
        telegram_api, "call", side_effect=telegram_api.TelegramError(401, "Unauthorized")
    ):
        response = admin_client.put("/api/v1/center/telegram/", {"token": "yomon"}, format="json")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_credentials"
    assert conf.telegram().token == ""


def test_disconnect_bot_removes_webhook_first(admin_client: APIClient) -> None:
    set_keys(telegram_token=TOKEN, telegram_username="bot", telegram_login=True)

    with patch.object(telegram_api, "call", return_value=True) as call:
        response = admin_client.delete("/api/v1/center/telegram/")

    assert response.status_code == 204
    assert call.call_args.args[0] == "deleteWebhook"
    row = Integrations.load()
    assert (row.telegram_token, row.telegram_username, row.telegram_login) == ("", "", False)


def test_bot_options_are_saved(admin_client: APIClient) -> None:
    set_keys(telegram_token=TOKEN)

    response = admin_client.patch(
        "/api/v1/center/telegram/",
        {"leads_chat": "-1001", "reports_chat": "-1002", "login": True},
        format="json",
    )

    assert response.status_code == 200
    bot = conf.telegram()
    assert (bot.leads_chat, bot.reports_chat, bot.login) == ("-1001", "-1002", True)


def test_click_secret_is_required_once_and_kept(admin_client: APIClient) -> None:
    body = {"service_id": "11", "merchant_id": "22"}

    missing = admin_client.put("/api/v1/center/click/", body, format="json")
    assert missing.status_code == 400

    saved = admin_client.put(
        "/api/v1/center/click/", {**body, "secret_key": "birinchi"}, format="json"
    )
    assert saved.status_code == 200

    kept = admin_client.put(
        "/api/v1/center/click/", {**body, "service_id": "33", "secret_key": ""}, format="json"
    )
    assert kept.status_code == 200
    assert conf.click().service_id == "33"
    assert conf.click().secret_key == "birinchi"

    assert admin_client.delete("/api/v1/center/click/").status_code == 204
    assert not conf.click().ready


def test_eskiz_is_checked_before_saving(admin_client: APIClient) -> None:
    body = {"email": "a@b.uz", "password": "parol", "sender": "4546"}

    with patch.object(sms, "can_login", return_value=False):
        rejected = admin_client.put("/api/v1/center/eskiz/", body, format="json")
    assert rejected.status_code == 400
    assert not conf.eskiz().ready

    with patch.object(sms, "can_login", return_value=True):
        accepted = admin_client.put("/api/v1/center/eskiz/", body, format="json")
    assert accepted.status_code == 200
    assert conf.eskiz().ready


def test_closed_sections_cannot_be_connected(admin_client: APIClient) -> None:
    use_plan(features=[])

    bot = admin_client.put("/api/v1/center/telegram/", {"token": TOKEN}, format="json")
    click = admin_client.put(
        "/api/v1/center/click/",
        {"service_id": "1", "merchant_id": "2", "secret_key": "3"},
        format="json",
    )
    setup = admin_client.get(SETUP).json()

    assert bot.status_code == 403
    assert click.status_code == 403
    assert setup["telegram"]["available"] is False
    assert setup["click"]["available"] is False


def test_brand_is_saved_and_shown(admin_client: APIClient) -> None:
    response = admin_client.patch(
        "/api/v1/center/brand/",
        {"name": "Yangi nom", "color": "#2563eb", "logo": logo_file()},
        format="multipart",
    )

    assert response.status_code == 200
    body = APIClient().get(INFO).json()
    assert body["name"] == "Yangi nom"
    assert body["color"] == "#2563eb"
    assert body["logo"]
    assert Center.objects.get(schema_name=connection.schema_name).name == "Yangi nom"

    removed = admin_client.patch("/api/v1/center/brand/", {"logo": None}, format="json")
    assert removed.status_code == 200
    assert APIClient().get(INFO).json()["logo"] == ""


@pytest.mark.parametrize(
    "changes",
    [
        {"color": "red;}body{display:none"},
        {"name": "A<script>"},
        {"name": "x"},
    ],
)
def test_bad_brand_is_rejected(admin_client: APIClient, changes: dict[str, str]) -> None:
    assert admin_client.patch("/api/v1/center/brand/", changes, format="json").status_code == 400


def test_gif_logo_is_rejected(admin_client: APIClient) -> None:
    response = admin_client.patch(
        "/api/v1/center/brand/", {"logo": logo_file("a.gif", "GIF")}, format="multipart"
    )

    assert response.status_code == 400
    assert not SiteSettings.load().logo


# --- SMS va ogohlantirish ---


@pytest.fixture
def real_sms(settings: Any) -> Iterator[None]:
    settings.SMS_DRY_RUN = False
    settings.ESKIZ_EMAIL = "platform@b.uz"
    settings.ESKIZ_PASSWORD = "platform-parol"
    settings.ESKIZ_FROM = "4546"
    yield


def test_code_uses_own_eskiz_when_connected(
    real_sms: None, django_capture_on_commit_callbacks: Any
) -> None:
    set_keys(eskiz_email="markaz@b.uz", eskiz_password="markaz-parol")

    with (
        patch("apps.notifications.tasks.send_sms_task.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        user_services.send_code_sms("+998901234567", "111222")

    args, kwargs = delay.call_args
    assert args[1].startswith("Test markaz: tasdiqlash kodi 111222")
    assert kwargs == {"platform": False}


def test_code_falls_back_to_platform_account(
    real_sms: None, django_capture_on_commit_callbacks: Any
) -> None:
    with (
        patch("apps.notifications.tasks.send_sms_task.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        user_services.send_code_sms("+998901234567", "111222")

    args, kwargs = delay.call_args
    assert args[1].startswith("Test platforma: tasdiqlash kodi 111222")
    assert kwargs == {"platform": True}


def test_platform_account_is_really_used(real_sms: None) -> None:
    responses = [(200, {"data": {"token": "t"}}), (200, {"id": "1"})]
    with patch("apps.notifications.sms._post", side_effect=responses) as post:
        notification_tasks.send_sms_task("+998901234567", "matn", platform=True)

    assert post.call_args_list[0].args[1]["email"] == "platform@b.uz"
    assert connection.schema_name != get_public_schema_name()


def test_platform_sms_quota(real_sms: None) -> None:
    use_plan(otp_sms_monthly=2)

    otp.issue_code("+998901000001", "register")
    otp.issue_code("+998901000002", "register")

    with pytest.raises(otp.OtpQuotaError):
        otp.issue_code("+998901000003", "register")


def test_own_eskiz_has_no_quota(real_sms: None) -> None:
    use_plan(otp_sms_monthly=0)
    set_keys(eskiz_email="markaz@b.uz", eskiz_password="markaz-parol")

    assert otp.issue_code("+998901000004", "register")


def test_alert_goes_to_platform_bot_with_center_name(settings: Any) -> None:
    settings.TELEGRAM_BOT_TOKEN = "platforma-tokeni"
    settings.TELEGRAM_ALERTS_CHAT_ID = "-100500"
    set_keys(telegram_token=TOKEN)
    used: list[str] = []

    def fake(method: str, payload: dict[str, Any], **_: Any) -> dict[str, Any]:
        used.append(conf.telegram().token)
        return {}

    with (
        patch.object(telegram_api, "call", side_effect=fake),
        patch(
            "apps.notifications.tasks.send_alert_task.delay",
            side_effect=notification_tasks.send_alert_task,
        ) as delay,
    ):
        assert alerts.alert("video:failed", "xato")

    assert used == ["platforma-tokeni"]
    assert "Test markaz: video:failed" in delay.call_args.args[0]


# --- AI budjeti ---


def test_center_budget_cannot_exceed_plan() -> None:
    use_plan(ai_monthly_usd=Decimal("10"))
    config = AssistantSettings.load()
    config.monthly_budget_usd = Decimal("100")

    assert monthly_limit(config) == Decimal("10")

    Center.objects.filter(schema_name=connection.schema_name).update(ai_monthly_usd=Decimal("50"))
    connection.set_tenant(
        Center.objects.select_related("plan").get(schema_name=connection.schema_name)
    )
    assert monthly_limit(config) == Decimal("50")


def test_click_callback_is_rejected_without_keys() -> None:
    body = {
        "click_trans_id": "1",
        "service_id": "1",
        "merchant_trans_id": "1",
        "amount": "1000",
        "action": "0",
        "sign_time": "2026-01-01 00:00:00",
        "sign_string": "x",
    }

    response = APIClient().post("/api/v1/payments/click/prepare/", body)

    assert response.json()["error"] == -1


def test_platform_sms_per_ip_cap(real_sms: None) -> None:
    for number in range(otp.PLATFORM_SMS_PER_IP):
        otp.issue_code(f"+99890200{number:04d}", "register", ip="10.0.0.1")

    with pytest.raises(otp.OtpQuotaError):
        otp.issue_code("+998902009999", "register", ip="10.0.0.1")


def test_sms_brand_stays_as_approved_after_rename(
    real_sms: None, django_capture_on_commit_callbacks: Any
) -> None:
    set_keys(eskiz_email="markaz@b.uz", eskiz_password="markaz-parol", eskiz_brand="Eski nom")

    with (
        patch("apps.notifications.tasks.send_sms_task.delay") as delay,
        django_capture_on_commit_callbacks(execute=True),
    ):
        user_services.send_code_sms("+998901234567", "111222")

    assert delay.call_args.args[1].startswith("Eski nom: tasdiqlash kodi 111222")


def test_platform_daily_sms_cap(real_sms: None, settings: Any) -> None:
    settings.PLATFORM_SMS_DAILY = 2

    with schema_context(get_public_schema_name()), patch("apps.users.otp.alert") as alert:
        otp.issue_code("+998903000001", "signup")
        otp.issue_code("+998903000002", "signup")
        with pytest.raises(otp.OtpQuotaError):
            otp.issue_code("+998903000003", "signup")

    alert.assert_called_once()


def test_disk_limit_counts_uploads_since_last_refresh() -> None:
    use_plan(max_disk_gb=1)

    check_disk(600 * 1024**2)

    with pytest.raises(LimitReached):
        check_disk(600 * 1024**2)
    check_disk(100 * 1024**2)


def test_renamed_center_is_in_the_same_response(admin_client: APIClient) -> None:
    response = admin_client.patch("/api/v1/center/brand/", {"name": "Yangi nom"}, format="json")

    assert response.json()["name"] == "Yangi nom"
