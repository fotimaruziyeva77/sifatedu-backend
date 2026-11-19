"""SMM agent: reja, tayyorlash, botda tasdiq va kanalga chiqarish (Gemini va Telegram soxta)."""

from collections.abc import Iterator
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any
from unittest import mock

import pytest
from django.core.cache import cache
from django.utils import timezone
from PIL import Image

from apps.bot.router import handle_update
from apps.bot.tests.conftest import FakeTelegram, connect, make_user, press
from apps.core.storage import public_storage
from apps.integrations.testing import set_keys
from apps.notifications import telegram
from apps.smm import ai, instagram, render, services, tasks
from apps.smm.models import Post, SmmSettings
from apps.users.roles import Role

pytestmark = pytest.mark.django_db

ADMIN_CHAT = 7001


class AlbumTelegram(FakeTelegram):
    def __call__(self, method: str, payload: dict[str, Any], **kwargs: Any) -> Any:
        if method == "sendMediaGroup":
            self.calls.append((method, payload))
            return [{"message_id": 500 + index} for index, _ in enumerate(payload["media"])]
        return super().__call__(method, payload, files=kwargs.get("files"))


@pytest.fixture
def tg() -> Iterator[AlbumTelegram]:
    cache.clear()
    set_keys(telegram_token="test-token")
    fake = AlbumTelegram()
    with mock.patch.object(telegram, "call", fake):
        yield fake


@pytest.fixture
def enabled(settings: Any) -> SmmSettings:
    settings.GEMINI_API_KEY = "test"
    row = SmmSettings.load()
    row.enabled = True
    row.channel = "@sifat_test"
    row.save()
    return row


def fake_plan(slots: list[Post], recent: list[str]) -> Decimal:
    for index, post in enumerate(slots):
        post.topic = f"Mavzu {index}"
        post.angle = "G'oya"
    return Decimal("0.009")


def draft(**extra: Any) -> ai.Draft:
    values: dict[str, Any] = {
        "lead": "Farzandingiz kuniga",
        "key": "5 soat",
        "tail": "telefonda. Bu yiliga 76 kun.",
        "glyph": "76",
        "slides": [ai.Slide(title="Birinchi qadam", body="Kuniga 20 daqiqa kod.")] * 3,
        "roles": [],
        "props": [],
        "scenes": [],
        "caption_ig": "Instagram matni #sifat",
        "caption_tg": "Telegram matni",
    }
    values.update(extra)
    return ai.Draft(**values)


def approver() -> None:
    connect(make_user("+998909000101", Role.ADMIN, name="Rahbar"), chat_id=ADMIN_CHAT)


def is_jpeg_of(data: bytes, size: tuple[int, int]) -> bool:
    image = Image.open(BytesIO(data))
    return image.format == "JPEG" and image.size == size


def test_render_cover_and_slide() -> None:
    cover = render.jpeg(render.cover("Farzandingiz kuniga", "5 soat", "telefonda", "76", "foydali"))
    page = render.jpeg(render.slide("Sarlavha", "Matn " * 40, 2, "2/4"))
    assert is_jpeg_of(cover, (1080, 1350))
    assert is_jpeg_of(page, (1080, 1350))


def test_week_plan_creates_slots_once(enabled: SmmSettings) -> None:
    with mock.patch.object(ai, "plan", fake_plan):
        created = services.plan_week(date(2026, 11, 23))
        again = services.plan_week(date(2026, 11, 23))
    assert len(created) == len(services.WEEK)
    assert again == []
    scripts = Post.objects.filter(kind=Post.Kind.SCRIPT)
    assert scripts.count() == 2
    first = Post.objects.filter(kind=Post.Kind.CAROUSEL).order_by("publish_at").first()
    assert first is not None
    assert timezone.localtime(first.publish_at).hour == enabled.publish_hour


def test_mid_week_plan_fills_only_the_rest(enabled: SmmSettings) -> None:
    thursday_noon = timezone.make_aware(datetime(2026, 11, 19, 12, 0))
    with mock.patch.object(ai, "plan", fake_plan):
        created = services.plan_week(date(2026, 11, 16), now=thursday_noon)
        again = services.plan_week(date(2026, 11, 16), now=thursday_noon)
    # Payshanba 10:00 dagi ssenariy o'tib ketgan; payshanba kechqurundan yakshanbagacha — 4 ta.
    assert len(created) == 4
    assert all(post.publish_at > thursday_noon for post in created)
    assert again == []


def test_enabled_agent_plans_current_week_by_itself(enabled: SmmSettings) -> None:
    with mock.patch.object(tasks.plan_week, "delay") as planner:
        tasks.prepare_due()
    planner.assert_called_once_with(current=True)

    make_post(publish_at=timezone.now() + timedelta(minutes=1))
    with mock.patch.object(tasks.plan_week, "delay") as planner:
        tasks.prepare_due()
    planner.assert_not_called()


def test_disabled_agent_does_nothing(settings: Any) -> None:
    settings.GEMINI_API_KEY = "test"
    with mock.patch.object(ai, "plan") as planner:
        assert tasks.plan_week() == 0
    planner.assert_not_called()


def make_post(kind: str = Post.Kind.CAROUSEL, **extra: Any) -> Post:
    return Post.objects.create(
        kind=kind,
        formula=Post.Formula.QUESTION if kind != Post.Kind.SCRIPT else Post.Formula.FAMILY,
        topic="Telefon va vaqt",
        publish_at=extra.pop("publish_at", timezone.now() + timedelta(hours=5)),
        **extra,
    )


def test_prepare_renders_and_sends_for_review(tg: AlbumTelegram, enabled: SmmSettings) -> None:
    approver()
    post = make_post()
    with mock.patch.object(ai, "write", return_value=(draft(), Decimal("0.01"))):
        tasks.prepare(post.pk)
    post.refresh_from_db()
    assert post.status == Post.Status.REVIEW
    assert len(post.images) == 4  # muqova + 3 slayd
    assert public_storage().exists(post.images[0])
    assert tg.of("sendMediaGroup")[0]["chat_id"] == ADMIN_CHAT
    review = tg.messages[-1]
    assert "Instagram matni" in review["text"]
    assert [
        b["callback_data"] for row in review["reply_markup"]["inline_keyboard"] for b in row
    ] == [
        f"sm:ok:{post.pk}",
        f"sm:re:{post.pk}",
        f"sm:no:{post.pk}",
    ]
    assert post.review_messages == [{"chat": ADMIN_CHAT, "message": review_id(tg)}]


def review_id(tg: AlbumTelegram) -> int:
    return tg.next_id


def test_approve_then_publish_to_channel(tg: AlbumTelegram, enabled: SmmSettings) -> None:
    approver()
    post = make_post(publish_at=timezone.now() + timedelta(hours=3))
    with mock.patch.object(ai, "write", return_value=(draft(), Decimal("0.01"))):
        tasks.prepare(post.pk)
    handle_update(press(f"sm:ok:{post.pk}", sender={"id": ADMIN_CHAT, "first_name": "Rahbar"}))
    post.refresh_from_db()
    assert post.status == Post.Status.APPROVED
    assert post.decided_by is not None
    assert "Tasdiqladi" in tg.edits[-1]["text"]

    tg.clear()
    Post.objects.filter(pk=post.pk).update(publish_at=timezone.now() - timedelta(minutes=1))
    tasks.publish_due()
    post.refresh_from_db()
    assert post.status == Post.Status.PUBLISHED
    album = tg.of("sendMediaGroup")[0]
    assert album["chat_id"] == "@sifat_test"
    assert album["media"][0]["caption"] == "Telegram matni"


def test_student_cannot_approve(tg: AlbumTelegram, enabled: SmmSettings) -> None:
    connect(make_user("+998909000102", name="O'quvchi"), chat_id=7002)
    post = make_post(status=Post.Status.REVIEW)
    handle_update(press(f"sm:ok:{post.pk}", sender={"id": 7002, "first_name": "O'quvchi"}))
    post.refresh_from_db()
    assert post.status == Post.Status.REVIEW
    assert "faqat SMM" in tg.notices[-1]


def test_redo_and_reject(
    tg: AlbumTelegram, enabled: SmmSettings, django_capture_on_commit_callbacks: Any
) -> None:
    approver()
    sender = {"id": ADMIN_CHAT, "first_name": "Rahbar"}
    post = make_post(status=Post.Status.REVIEW)
    with (
        mock.patch.object(tasks.prepare, "delay") as again,
        django_capture_on_commit_callbacks(execute=True),
    ):
        handle_update(press(f"sm:re:{post.pk}", sender=sender))
    post.refresh_from_db()
    assert post.status == Post.Status.PLANNED
    assert post.attempts == 1
    again.assert_called_once_with(post.pk)

    other = make_post(status=Post.Status.REVIEW)
    handle_update(press(f"sm:no:{other.pk}", sender=sender))
    other.refresh_from_db()
    assert other.status == Post.Status.REJECTED
    handle_update(press(f"sm:ok:{other.pk}", sender=sender))
    other.refresh_from_db()
    assert other.status == Post.Status.REJECTED


def test_script_is_delivered_but_never_published(tg: AlbumTelegram, enabled: SmmSettings) -> None:
    approver()
    post = make_post(Post.Kind.SCRIPT, publish_at=timezone.now() - timedelta(minutes=5))
    scene = ai.Scene(seconds="0–3", shot="yaqin", action="Ona eshikda", line="Yana telefonmi?")
    script = draft(slides=[], roles=["Ona", "O'g'il, 12 yosh"], props=["noutbuk"], scenes=[scene])
    with mock.patch.object(ai, "write", return_value=(script, Decimal("0.01"))):
        tasks.prepare(post.pk)
    assert "Suratga olish ssenariysi" in tg.messages[-1]["text"]
    assert "Yana telefonmi?" in tg.messages[-1]["text"]
    handle_update(press(f"sm:ok:{post.pk}", sender={"id": ADMIN_CHAT, "first_name": "Rahbar"}))
    tg.clear()
    tasks.publish_due()
    post.refresh_from_db()
    assert post.status == Post.Status.APPROVED
    assert tg.of("sendMediaGroup") == [] and tg.of("sendPhoto") == []


def test_unanswered_post_expires(tg: AlbumTelegram, enabled: SmmSettings) -> None:
    post = make_post(
        status=Post.Status.REVIEW,
        publish_at=timezone.now() - services.GRACE - timedelta(minutes=1),
        review_messages=[{"chat": ADMIN_CHAT, "message": 9}],
    )
    tasks.publish_due()
    post.refresh_from_db()
    assert post.status == Post.Status.REJECTED
    assert "tasdiqlanmadi" in tg.edits[-1]["text"]


def test_failed_generation_is_recorded(enabled: SmmSettings) -> None:
    post = make_post()
    with mock.patch.object(ai, "write", side_effect=ai.AiError("AI javob bermadi")) as writer:
        tasks.prepare(post.pk)
    post.refresh_from_db()
    # Ikki marta qayta urinib, keyin xato.
    assert writer.call_count == tasks.MAX_ATTEMPTS
    assert post.status == Post.Status.FAILED
    assert "AI javob bermadi" in post.error


def test_render_cleans_unsupported_characters() -> None:
    assert render.clean("Oʻqish 🚀 → kod") == "O‘qish - kod"
    assert render.clean("g`oya") == "g’oya"


def test_stuck_post_is_requeued_and_old_slots_are_dropped(enabled: SmmSettings) -> None:
    stuck = make_post(status=Post.Status.MAKING)
    Post.objects.filter(pk=stuck.pk).update(updated_at=timezone.now() - timedelta(minutes=30))
    old = make_post(publish_at=timezone.now() - timedelta(days=2))
    with (
        mock.patch.object(tasks.prepare, "delay") as queued,
        mock.patch.object(tasks.plan_week, "delay"),
    ):
        tasks.prepare_due()
    stuck.refresh_from_db()
    old.refresh_from_db()
    assert stuck.status == Post.Status.PLANNED and stuck.attempts == 1
    assert old.status == Post.Status.REJECTED
    queued.assert_called_once_with(stuck.pk)


def test_late_approved_post_is_not_published(tg: AlbumTelegram, enabled: SmmSettings) -> None:
    post = make_post(
        status=Post.Status.APPROVED,
        publish_at=timezone.now() - services.LATE_PUBLISH - timedelta(minutes=1),
    )
    tasks.publish_due()
    post.refresh_from_db()
    assert post.status == Post.Status.REJECTED
    assert tg.of("sendMediaGroup") == []


def test_partial_publish_is_recorded(tg: AlbumTelegram, enabled: SmmSettings) -> None:
    approver()
    post = make_post()
    long_text = "Uzun matn " * 150  # rasm izohiga sig'maydi — alohida xabar
    with mock.patch.object(ai, "write", return_value=(draft(caption_tg=long_text), Decimal("0"))):
        tasks.prepare(post.pk)
    Post.objects.filter(pk=post.pk).update(
        status=Post.Status.APPROVED, publish_at=timezone.now() - timedelta(minutes=1)
    )
    tg.errors["sendMessage"] = telegram.TelegramError(400, "can't parse entities")
    tasks.publish(post.pk)
    post.refresh_from_db()
    assert post.status == Post.Status.FAILED
    assert post.channel_messages == [500, 501, 502, 503]
    assert post.error.startswith("Kanalga qisman chiqdi")


def test_late_approval_publishes_after_commit(
    tg: AlbumTelegram, enabled: SmmSettings, django_capture_on_commit_callbacks: Any
) -> None:
    approver()
    post = make_post(publish_at=timezone.now() - timedelta(minutes=1))
    with mock.patch.object(ai, "write", return_value=(draft(), Decimal("0"))):
        tasks.prepare(post.pk)
    with mock.patch.object(tasks.publish, "delay") as queued:
        with django_capture_on_commit_callbacks(execute=False) as callbacks:
            sender = {"id": ADMIN_CHAT, "first_name": "Rahbar"}
            handle_update(press(f"sm:ok:{post.pk}", sender=sender))
        queued.assert_not_called()  # tranzaksiya yopilmaguncha navbatga qo'yilmaydi
        for callback in callbacks:
            callback()
    queued.assert_called_once_with(post.pk)


class FakeInstagram:
    """graph.instagram.com o'rniga: chaqiruvlarni yozadi, konteyner ID larini beradi."""

    def __init__(self, fail_publish: bool = False) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.fail_publish = fail_publish
        self.next = 0

    def __call__(
        self, method: str, path: str, params: dict[str, Any], token: str, **_: Any
    ) -> dict[str, Any]:
        self.calls.append((method, path, params))
        if path == "me":
            return {"data": [{"user_id": "1789", "username": "sifatedu"}]}
        if path.endswith("/media_publish"):
            if self.fail_publish:
                raise instagram.InstagramError("Instagram: limit")
            return {"id": "ig-post-1"}
        if path.endswith("/media"):
            self.next += 1
            return {"id": f"c{self.next}"}
        if params.get("fields") == "status_code":
            return {"status_code": "FINISHED"}
        if params.get("fields") == "permalink":
            return {"permalink": "https://www.instagram.com/p/abc/"}
        if path == "refresh_access_token":
            return {"access_token": "fresh-token"}
        return {}


@pytest.fixture
def ig_settings(enabled: SmmSettings) -> SmmSettings:
    enabled.instagram = True
    enabled.ig_token = "ig-token"
    enabled.ig_user_id = "1789"
    enabled.save()
    return enabled


def approved_carousel() -> Post:
    approver()
    post = make_post()
    with mock.patch.object(ai, "write", return_value=(draft(), Decimal("0"))):
        tasks.prepare(post.pk)
    Post.objects.filter(pk=post.pk).update(
        status=Post.Status.APPROVED, publish_at=timezone.now() - timedelta(minutes=1)
    )
    return post


def test_carousel_goes_to_instagram_and_telegram(
    tg: AlbumTelegram, ig_settings: SmmSettings
) -> None:
    post = approved_carousel()
    fake = FakeInstagram()
    with mock.patch.object(instagram, "request", fake):
        tasks.publish(post.pk)
    post.refresh_from_db()
    assert post.status == Post.Status.PUBLISHED
    assert post.ig_media_id == "ig-post-1"
    assert post.ig_permalink == "https://www.instagram.com/p/abc/"
    media = [params for method, path, params in fake.calls if path == "1789/media"]
    assert [m.get("is_carousel_item") for m in media[:4]] == ["true"] * 4
    parent = media[-1]
    assert parent["media_type"] == "CAROUSEL" and parent["children"] == "c1,c2,c3,c4"
    assert parent["caption"] == "Instagram matni #sifat"
    assert all(
        public_storage().url(name) in [m.get("image_url") for m in media] for name in post.images
    )
    assert tg.of("sendMediaGroup")[-1]["chat_id"] == "@sifat_test"


def test_instagram_failure_keeps_telegram_and_retries_only_instagram(
    tg: AlbumTelegram, ig_settings: SmmSettings
) -> None:
    post = approved_carousel()
    with mock.patch.object(instagram, "request", FakeInstagram(fail_publish=True)):
        tasks.publish(post.pk)
    post.refresh_from_db()
    assert post.status == Post.Status.FAILED
    assert post.channel_messages and not post.ig_media_id
    assert "limit" in post.error

    tg.clear()
    Post.objects.filter(pk=post.pk).update(status=Post.Status.APPROVED)
    with mock.patch.object(instagram, "request", FakeInstagram()):
        tasks.publish(post.pk)
    post.refresh_from_db()
    assert post.status == Post.Status.PUBLISHED
    assert post.ig_media_id == "ig-post-1"
    assert tg.of("sendMediaGroup") == []  # Telegram'ga ikkinchi marta chiqmadi


def test_connect_and_refresh_instagram(enabled: SmmSettings) -> None:
    enabled.ig_token = "ig-token"
    enabled.save()
    with mock.patch.object(instagram, "request", FakeInstagram()):
        assert services.connect_instagram() == "sifatedu"
        assert tasks.refresh_instagram() is True
    row = SmmSettings.load()
    assert row.ig_user_id == "1789"
    assert row.ig_token == "fresh-token"
    assert row.ig_token_refreshed_at is not None


def test_instagram_error_hides_token() -> None:
    error = instagram.urllib.error.HTTPError(
        "https://graph.instagram.com",
        400,
        "Bad",
        {},  # type: ignore[arg-type]
        BytesIO(b'{"error": {"message": "Invalid"}}'),
    )
    with (
        mock.patch.object(instagram.urllib.request, "urlopen", side_effect=error),
        pytest.raises(instagram.InstagramError) as caught,
    ):
        instagram.request("GET", "me", {}, "secret-token")
    assert "secret-token" not in str(caught.value)
    assert "Invalid" in str(caught.value)


def test_instagram_retry_reuses_container_and_skips_published(
    tg: AlbumTelegram, ig_settings: SmmSettings
) -> None:
    post = approved_carousel()
    with mock.patch.object(instagram, "request", FakeInstagram(fail_publish=True)):
        tasks.publish(post.pk)
    post.refresh_from_db()
    assert post.ig_container_id == "c5"

    retry = FakeInstagram()
    Post.objects.filter(pk=post.pk).update(status=Post.Status.APPROVED)
    with mock.patch.object(instagram, "request", retry):
        tasks.publish(post.pk)
    assert not [call for call in retry.calls if call[1] == "1789/media"]  # yangi konteyner yo'q
    assert ("POST", "1789/media_publish", {"creation_id": "c5"}) in retry.calls


def test_expired_token_turns_instagram_off(tg: AlbumTelegram, ig_settings: SmmSettings) -> None:
    post = approved_carousel()
    expired = instagram.InstagramError("Instagram: Error validating access token", code=190)
    with mock.patch.object(instagram, "request", side_effect=expired):
        tasks.publish(post.pk)
    row = SmmSettings.load()
    assert row.instagram is False
    assert "yaroqsiz" in row.ig_error
    assert any("Instagram tokeni yaroqsiz" in text for text in tg.texts)


def test_redo_drops_rejected_version(tg: AlbumTelegram, enabled: SmmSettings) -> None:
    approver()
    post = make_post(status=Post.Status.REVIEW, images=["smm/x.jpg"], caption="eski")
    with mock.patch.object(tasks.prepare, "delay"):
        handle_update(press(f"sm:re:{post.pk}", sender={"id": ADMIN_CHAT, "first_name": "Rahbar"}))
    post.refresh_from_db()
    assert post.images == [] and post.caption == "" and post.decided_by is None


def test_busy_model_falls_back_to_next(settings: Any) -> None:
    from google.genai import errors as genai_errors

    settings.GEMINI_API_KEY = "test"
    settings.SMM_GEMINI_MODEL = "asosiy"
    settings.SMM_GEMINI_FALLBACKS = ["zaxira"]
    busy = genai_errors.ServerError(503, {"error": {"code": 503, "message": "band"}})
    answer = mock.Mock(parsed=ai.Plan(items=[]), usage_metadata=None)
    calls: list[str] = []

    def generate(*, model: str, **_: Any) -> Any:
        calls.append(model)
        if model == "asosiy":
            raise busy
        return answer

    with mock.patch.object(ai.genai, "Client") as client:
        client.return_value.models.generate_content.side_effect = generate
        result, _ = ai.ask("s", "p", ai.Plan)
    assert calls == ["asosiy", "zaxira"]
    assert result.items == []
