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

from . import ai, render, review
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
    Post.objects.filter(pk=post.pk).update(
        status=Post.Status.PLANNED, attempts=F("attempts") + 1, error=""
    )
    from .tasks import prepare

    transaction.on_commit(lambda: prepare.delay(post.pk))


def publish(post: Post) -> None:
    """Telegram kanalga. Instagram API ulangunga qadar Instagram'ga qo'lda qo'yiladi
    (rasmlar va matn tasdiq xabarida)."""
    channel = SmmSettings.load().channel.strip()
    if not channel:
        raise tg.ChannelError("Telegram kanal ko'rsatilmagan (SMM sozlamalari).")

    def sent(message: dict[str, Any]) -> None:
        # Har yuborilgan xabar darhol yoziladi: keyingi qadam yiqilsa, kanalda nima
        # qolgani ma'lum bo'ladi va post qayta yasalib, ikkinchi marta chiqmaydi.
        post.channel_messages = [*post.channel_messages, message.get("message_id")]
        Post.objects.filter(pk=post.pk).update(channel_messages=post.channel_messages)

    post.channel_messages = []
    tg.send_album(channel, post.images, tg.html(post.caption_tg or post.caption), on_sent=sent)
    post.status = Post.Status.PUBLISHED
    post.published_at = timezone.now()
    post.error = ""
    post.save(update_fields=["channel_messages", "status", "published_at", "error", "updated_at"])
    review.mark(post, "📣 Kanalga chiqdi")


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
