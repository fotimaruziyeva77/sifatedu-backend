"""SMM agent ish oqimi: reja → tayyorlash (matn + rasm) → tasdiq → kanalga chiqarish."""

import logging
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.core.storage import public_storage

from . import ai, instagram, render, review
from . import telegram as tg
from .models import Post, SmmSettings

logger = logging.getLogger(__name__)

K, F_ = Post.Kind, Post.Formula
# Hafta (0 — dushanba): har kuni bitta chiqadigan post + 2 ta suratga olish ssenariysi.
# Ssenariylar kanalga chiqmaydi: ertalab tasdiqlovchiga yuboriladi, markaz suratga oladi.
WEEK: list[tuple[int, str, str]] = [
    (0, K.SCRIPT, F_.FAMILY),
    (0, K.CAROUSEL, F_.TIPS),
    (1, K.POST, F_.QUESTION),
    (2, K.POST, F_.HUMOR),
    (3, K.SCRIPT, F_.RESULT),
    (3, K.CAROUSEL, F_.INSIDE),
    (4, K.CAROUSEL, F_.STORY),
    (5, K.CAROUSEL, F_.TIPS),
    (6, K.POST, F_.QUESTION),
]
SCRIPT_HOUR = 10
# Post chiqishidan shuncha oldin tayyorlanadi va tasdiqqa yuboriladi.
LEAD = timedelta(hours=30)
# Tasdiqlanmagan post chiqish vaqtidan keyin shuncha kutadi, so'ng bekor bo'ladi.
GRACE = timedelta(hours=2)
# Tasdiqlangan, lekin server ishlamagani uchun kechikkan post shuncha vaqtgacha chiqariladi.
LATE_PUBLISH = timedelta(hours=6)
TAGS = {
    F_.FAMILY: "oila",
    F_.RESULT: "natija",
    F_.QUESTION: "ota-onalarga",
    F_.INSIDE: "it ichidan",
    F_.TIPS: "foydali",
    F_.HUMOR: "hazil",
    F_.STORY: "hikoya",
}


def week_start(today: date) -> date:
    """Keyingi dushanba."""
    return today + timedelta(days=7 - today.weekday())


def slot_time(day: date, kind: str, hour: int) -> datetime:
    at = time(SCRIPT_HOUR if kind == K.SCRIPT else hour)
    return timezone.make_aware(datetime.combine(day, at))


def plan_week(start: date | None = None) -> list[Post]:
    """Haftalik reja: o'rinlar yaratiladi, mavzularni AI yozadi. Hafta allaqachon rejalangan
    bo'lsa — hech narsa qilinmaydi."""
    settings = SmmSettings.load()
    start = start or week_start(timezone.localdate())
    begin = slot_time(start, K.POST, 0)
    if Post.objects.filter(
        publish_at__gte=begin, publish_at__lt=begin + timedelta(days=7)
    ).exists():
        return []
    posts = [
        Post(
            kind=kind,
            formula=formula,
            publish_at=slot_time(start + timedelta(days=day), kind, settings.publish_hour),
        )
        for day, kind, formula in WEEK
    ]
    recent = list(Post.objects.order_by("-publish_at").values_list("topic", flat=True)[:40])
    spent = ai.plan(posts, recent)
    share = (spent / len(posts)).quantize(Decimal("0.0001"))
    for post in posts:
        post.cost_usd = share
    return Post.objects.bulk_create(posts)


def store(post: Post, index: int, data: bytes) -> str:
    name = f"smm/{post.pk}/{post.attempts}-{index:02d}.jpg"
    return public_storage().save(name, ContentFile(data))


def images_for(post: Post, draft: ai.Draft) -> list[bytes]:
    tag = TAGS.get(Post.Formula(post.formula), "")
    if post.kind != K.CAROUSEL:
        return [render.jpeg(render.cover(draft.lead, draft.key, draft.tail, draft.glyph, tag))]
    slides = draft.slides[:8]
    total = len(slides) + 1
    pages = [render.cover(draft.lead, draft.key, draft.tail, draft.glyph, tag, f"1/{total}")]
    pages += [
        render.slide(item.title, item.body, number, f"{number + 1}/{total}")
        for number, item in enumerate(slides, start=1)
    ]
    return [render.jpeg(page) for page in pages]


def make(post: Post) -> None:
    """Matn va rasmlar tayyorlanadi, keyin tasdiqqa (yoki avtomat rejimda — to'g'ridan
    navbatga). Xato tashqariga chiqadi — vazifa postni «xato» qiladi."""
    draft, spent = ai.write(post)
    post.content = draft.model_dump()
    post.caption = draft.caption_ig.strip()
    post.caption_tg = draft.caption_tg.strip()
    post.images = [store(post, index, data) for index, data in enumerate(images_for(post, draft))]
    post.cost_usd = (post.cost_usd or Decimal(0)) + spent
    post.error = ""
    auto = SmmSettings.load().auto_publish and post.publishable
    post.status = Post.Status.APPROVED if auto else Post.Status.REVIEW
    post.save()
    review.send(post, auto=auto)


def redo(post: Post) -> None:
    # Rad etilgan variant qolmasin: yangisi yiqilsa ham, eskisi kanalga chiqib ketmasin.
    Post.objects.filter(pk=post.pk).update(
        status=Post.Status.PLANNED,
        attempts=F("attempts") + 1,
        error="",
        images=[],
        caption="",
        caption_tg="",
        decided_by=None,
    )
    from .tasks import prepare

    transaction.on_commit(lambda: prepare.delay(post.pk))


class PublishError(RuntimeError):
    """Kamida bitta joyga (Telegram yoki Instagram) chiqmadi."""


def to_telegram(post: Post, channel: str) -> None:
    def sent(message: dict[str, Any]) -> None:
        # Har yuborilgan xabar darhol yoziladi: keyingi qadam yiqilsa, kanalda nima
        # qolgani ma'lum bo'ladi va post ikkinchi marta chiqmaydi.
        post.channel_messages = [*post.channel_messages, message.get("message_id")]
        Post.objects.filter(pk=post.pk).update(channel_messages=post.channel_messages)

    try:
        tg.send_album(channel, post.images, tg.html(post.caption_tg or post.caption), on_sent=sent)
    except OSError:
        # Javob kelmadi: albom kanalga tushgan bo'lishi mumkin. Qayta urinishda ikkinchi marta
        # yuborilmasin — belgi qo'yiladi, odam kanalni tekshiradi.
        if not post.channel_messages:
            post.channel_messages = [0]
            Post.objects.filter(pk=post.pk).update(channel_messages=post.channel_messages)
        raise PublishError(
            "Telegram javob bermadi — kanalni tekshiring, qayta yuborilmaydi."
        ) from None


def to_instagram(post: Post, settings: SmmSettings) -> None:
    token, user_id = settings.ig_token, settings.ig_user_id
    if post.ig_container_id:
        # Oldingi urinishda javob kelmagan: konteyner chiqib bo'lganmi?
        state = instagram.status(post.ig_container_id, token)
        if state == "PUBLISHED":
            post.ig_media_id = "published"
            Post.objects.filter(pk=post.pk).update(ig_media_id=post.ig_media_id)
            return
        if state != "FINISHED":
            post.ig_container_id = ""
    if not post.ig_container_id:
        storage = public_storage()
        urls = [storage.url(name) for name in post.images]
        post.ig_container_id = instagram.prepare(user_id, token, urls, post.caption)
        Post.objects.filter(pk=post.pk).update(ig_container_id=post.ig_container_id)
    media_id = instagram.publish(user_id, token, post.ig_container_id)
    post.ig_media_id = media_id
    Post.objects.filter(pk=post.pk).update(ig_media_id=media_id)
    post.ig_permalink = instagram.permalink(media_id, settings.ig_token)[:200]
    Post.objects.filter(pk=post.pk).update(ig_permalink=post.ig_permalink)


def publish(post: Post) -> None:
    """Telegram kanal va (yoqilgan bo'lsa) Instagram. Har biri alohida: biri yiqilsa, ikkinchisi
    baribir chiqadi; qayta urinishda chiqib bo'lgani o'tkazib yuboriladi (ikki marta emas)."""
    settings = SmmSettings.load()
    channel = settings.channel.strip()
    if not channel and not settings.instagram_ready:
        raise PublishError("Telegram kanal ham, Instagram ham sozlanmagan (SMM sozlamalari).")
    errors: list[str] = []
    if channel and not post.channel_messages:
        try:
            to_telegram(post, channel)
        except Exception as exc:
            logger.warning("SMM: Telegram kanalga chiqmadi (%s): %s", post.pk, exc)
            errors.append(f"Telegram: {exc}")
    if settings.instagram_ready and not post.ig_media_id:
        try:
            to_instagram(post, settings)
        except Exception as exc:
            logger.warning("SMM: Instagram'ga chiqmadi (%s): %s", post.pk, exc)
            errors.append(str(exc))
            if isinstance(exc, instagram.InstagramError) and exc.auth:
                instagram_broken(settings, str(exc))
    if errors:
        raise PublishError("; ".join(errors))
    post.status = Post.Status.PUBLISHED
    post.published_at = timezone.now()
    post.error = ""
    post.save(update_fields=["status", "published_at", "error", "updated_at"])
    where = []
    if post.channel_messages:
        where.append("Telegram")
    if post.ig_media_id:
        where.append(
            f'<a href="{post.ig_permalink}">Instagram</a>' if post.ig_permalink else "Instagram"
        )
    review.mark(post, "📣 Chiqdi: " + ", ".join(where))


def instagram_broken(settings: SmmSettings, reason: str) -> None:
    """Token yaroqsiz: Instagram o'chiriladi (har kuni xato bermasin), tasdiqlovchilarga xabar."""
    settings.instagram = False
    settings.ig_error = f"Token yaroqsiz, Instagram o'chirildi: {reason}"
    settings.save(update_fields=["instagram", "ig_error", "updated_at"])
    review.notify(
        "⚠️ Instagram tokeni yaroqsiz — Instagram'ga chiqarish o'chirildi. Admin → SMM "
        "sozlamalari: yangi token kiriting, «Instagram'ni tekshirish» va qayta yoqing."
    )


def refresh_instagram() -> bool:
    """Tokenni yangilaydi (u 24 soatdan katta bo'lishi kerak). Xatoni sozlamaga yozadi."""
    settings = SmmSettings.load()
    if not settings.ig_token:
        return False
    try:
        settings.ig_token = instagram.refresh(settings.ig_token)
    except instagram.InstagramError as exc:
        if exc.auth:
            instagram_broken(settings, str(exc))
        else:
            settings.ig_error = f"Token yangilanmadi: {exc}"
            settings.save(update_fields=["ig_error", "updated_at"])
        return False
    settings.ig_token_refreshed_at = timezone.now()
    settings.ig_error = ""
    settings.save(update_fields=["ig_token", "ig_token_refreshed_at", "ig_error", "updated_at"])
    return True


def connect_instagram() -> str:
    """Kiritilgan tokenni tekshiradi va hisob ID sini oladi. Qaytadi: @username."""
    settings = SmmSettings.load()
    if not settings.ig_token:
        raise instagram.InstagramError("Avval Instagram tokenini kiriting.")
    user_id, username = instagram.me(settings.ig_token)
    settings.ig_user_id, settings.ig_username = user_id, username
    settings.ig_error = ""
    if settings.ig_token_refreshed_at is None:
        settings.ig_token_refreshed_at = timezone.now()
    settings.save(
        update_fields=[
            "ig_user_id",
            "ig_username",
            "ig_error",
            "ig_token_refreshed_at",
            "updated_at",
        ]
    )
    return username


def expire_unanswered(now: datetime | None = None) -> int:
    """Vaqtida tasdiqlanmagan postlar bekor bo'ladi (keyingi kunga surilmaydi)."""
    now = now or timezone.now()
    late = list(Post.objects.filter(status=Post.Status.REVIEW, publish_at__lt=now - GRACE))
    for post in late:
        post.status = Post.Status.REJECTED
        post.error = "Vaqtida tasdiqlanmadi."
        post.save(update_fields=["status", "error", "updated_at"])
        review.mark(post, "⌛ Vaqtida tasdiqlanmadi — chiqmadi")
    return len(late)
