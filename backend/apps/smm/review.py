"""Tasdiq: tayyor post botda SMM huquqi bor xodimlarga keladi — «Chiqarish», «Qayta yasash»,
«Bekor». Telegram'i saytdagi akkauntiga ulangan va `smm.change_post` ruxsati borlar (admin,
menejer). Qaror qabul qilingach hamma tasdiqlovchidagi tugmalar olib tashlanadi."""

import logging
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.notifications import telegram
from apps.users.models import SocialAccount, User

from . import telegram as tg
from .models import Post, SmmSettings

logger = logging.getLogger(__name__)

PERMISSION = "smm.change_post"
WEEKDAYS = ("Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba")


def approvers() -> list[int]:
    accounts = SocialAccount.objects.filter(
        provider=SocialAccount.Provider.TELEGRAM, user__is_active=True
    ).select_related("user")
    return [
        int(account.uid)
        for account in accounts
        if account.uid.lstrip("-").isdigit() and account.user.has_perm(PERMISSION)
    ]


def when(post: Post) -> str:
    local = timezone.localtime(post.publish_at)
    return f"{WEEKDAYS[local.weekday()]}, {local:%d.%m %H:%M}"


def script_text(post: Post) -> str:
    content = post.content or {}
    lines = [f"🎬 <b>Suratga olish ssenariysi</b> · {post.get_formula_display()}", ""]
    lines.append(f"<b>{tg.html(post.topic)}</b>")
    if post.angle:
        lines += ["", tg.html(post.angle)]
    if content.get("roles"):
        lines += ["", "<b>Rollar:</b> " + tg.html(", ".join(content["roles"]))]
    if content.get("props"):
        lines.append("<b>Kerak:</b> " + tg.html(", ".join(content["props"])))
    scenes = content.get("scenes") or []
    if scenes:
        lines += ["", "<b>Kadrlar:</b>"]
        for scene in scenes:
            when_, shot = scene.get("seconds", ""), scene.get("shot", "")
            lines.append(tg.html(f"⏱ {when_} · {shot} — {scene.get('action', '')}"))
            if scene.get("line"):
                lines.append(f"   💬 <i>{tg.html(scene['line'])}</i>")
    lines += ["", "Telefonda vertikal (9:16) suratga oling. Rozilik olinganini unutmang."]
    return "\n".join(lines)


def post_text(post: Post, *, auto: bool) -> str:
    kind = post.get_kind_display().capitalize()
    head = f"📝 <b>{kind}</b> · {post.get_formula_display()} · {when(post)}"
    places = (
        "Telegram kanal va Instagram" if SmmSettings.load().instagram_ready else "Telegram kanal"
    )
    note = (
        f"Avtomatik chiqadi: {places}."
        if auto
        else f"Tasdiqlasangiz, shu vaqtda chiqadi: {places}."
    )
    return "\n\n".join(
        [
            head,
            f"<b>Instagram matni:</b>\n{tg.html(post.caption)}",
            f"<b>Telegram matni:</b>\n{tg.html(post.caption_tg)}",
            f"<i>{note}</i>",
        ]
    )


def buttons(post: Post) -> dict[str, Any]:
    ok = "✅ Qabul qilindi" if not post.publishable else "✅ Chiqarish"
    return {
        "inline_keyboard": [
            [{"text": ok, "callback_data": f"sm:ok:{post.pk}"}],
            [
                {"text": "🔄 Qayta yasash", "callback_data": f"sm:re:{post.pk}"},
                {"text": "✖️ Bekor", "callback_data": f"sm:no:{post.pk}"},
            ],
        ]
    }


def send(post: Post, *, auto: bool = False) -> None:
    """Tayyor post har bir tasdiqlovchiga: rasmlar, matnlar va tugmalar."""
    text = script_text(post) if not post.publishable else post_text(post, auto=auto)
    markup = None if auto else buttons(post)
    stored: list[dict[str, int]] = []
    for chat_id in approvers():
        try:
            sent = tg.send_album(
                chat_id, post.images, text[:4000], buttons=markup or {"inline_keyboard": []}
            )
        except (OSError, RuntimeError, telegram.TelegramNotConfiguredError) as exc:
            logger.warning("SMM post tasdiqqa yuborilmadi (chat %s): %s", chat_id, exc)
            continue
        last = sent[-1] if sent else {}
        if last.get("message_id"):
            stored.append({"chat": chat_id, "message": int(last["message_id"])})
    post.review_messages = stored
    post.save(update_fields=["review_messages", "updated_at"])


def notify(text: str) -> None:
    """Tasdiqlovchilarga oddiy xabar (masalan, Instagram tokeni yaroqsiz)."""
    for chat_id in approvers():
        try:
            telegram.send_message(chat_id, text)
        except (OSError, RuntimeError, telegram.TelegramNotConfiguredError) as exc:
            logger.info("SMM xabari yuborilmadi (chat %s): %s", chat_id, exc)


def mark(post: Post, status_line: str) -> None:
    """Tasdiqlovchilardagi xabar: tugmalar o'rniga qaror."""
    text = f"<b>{tg.html(post.topic)}</b>\n\n{status_line}"
    for item in post.review_messages or []:
        try:
            telegram.edit_message(
                item["chat"], item["message"], text, reply_markup={"inline_keyboard": []}
            )
        except (OSError, RuntimeError, telegram.TelegramNotConfiguredError, KeyError) as exc:
            logger.info("SMM tasdiq xabari yangilanmadi: %s", exc)


def on_button(user: User | None, args: list[str]) -> str:
    """Botdagi tugma (`sm:<ok|re|no>:<id>`). Qaytadi: qisqa javob."""
    from . import services

    if user is None or not user.has_perm(PERMISSION):
        return "Bu tugma faqat SMM huquqi borlar uchun."
    if len(args) != 2 or not args[1].isdigit():
        return ""
    action, post = args[0], Post.objects.select_for_update().filter(pk=int(args[1])).first()
    if post is None:
        return "Post topilmadi."
    if post.status != Post.Status.REVIEW:
        return f"Qaror qabul qilingan: {post.get_status_display()}."
    name = user.first_name or user.phone
    post.decided_by = user
    if action == "ok":
        post.status = Post.Status.APPROVED
        post.save(update_fields=["status", "decided_by", "updated_at"])
        if post.publishable:
            mark(post, f"✅ Tasdiqladi: {tg.html(name)} · {when(post)} da chiqadi")
            if post.publish_at <= timezone.now():
                from .tasks import publish

                post_id = post.pk
                transaction.on_commit(lambda: publish.delay(post_id))
        else:
            mark(post, f"✅ Qabul qildi: {tg.html(name)} — suratga olishga")
        return "Tasdiqlandi."
    if action == "re":
        post.save(update_fields=["decided_by", "updated_at"])
        mark(post, f"🔄 {tg.html(name)}: qayta yasalmoqda…")
        services.redo(post)
        return "Qayta yasalmoqda."
    if action == "no":
        post.status = Post.Status.REJECTED
        post.save(update_fields=["status", "decided_by", "updated_at"])
        mark(post, f"✖️ Bekor qildi: {tg.html(name)}")
        return "Bekor qilindi."
    return ""
