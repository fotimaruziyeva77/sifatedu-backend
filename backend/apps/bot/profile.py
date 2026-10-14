"""Botda o'quvchi profili (22d): «Familiya Ism Otasining ismi» → tasdiq → tug'ilgan sana →
selfi («Keyinroq» mumkin). Faqat yetishmagan qadamlar so'raladi; «✏️ O'zgartirish» — hammasi.

Holat: `chat.state["profile"] = {"step", "at" (unix vaqt), "all", "name"}`. 30 daqiqadan eski
holat hisobga olinmaydi — yozilgan matn odatdagidek (AI maslahatchiga) ketadi. Rasm Celery'da
yuklab olinadi (`tasks.save_profile_photo`): Telegram'dan fayl olish bir necha soniya — bot qulfi
(`router.locked`) shuncha kutib turmasin.
"""

import logging
import time
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.notifications import telegram
from apps.users import photos
from apps.users import profile as person
from apps.users.models import SocialAccount, User

from .models import BotChat
from .send import Rows, button, escape, send
from .texts import t

logger = logging.getLogger(__name__)

KEY = "profile"
PUSHED = "profile_pushed"
TTL = 30 * 60
CONFIRM = "confirm"
ORDER = (person.NAME, person.BIRTH, person.PHOTO)


def current(chat: BotChat) -> dict[str, Any] | None:
    state = chat.state.get(KEY)
    if not isinstance(state, dict) or time.time() - float(state.get("at") or 0) > TTL:
        return None
    return state


def remember(chat: BotChat, step: str, **extra: Any) -> None:
    everything = bool((current(chat) or {}).get("all"))
    chat.state[KEY] = {"step": step, "at": int(time.time()), "all": everything, **extra}
    chat.save(update_fields=["state", "updated_at"])


def forget(chat: BotChat) -> None:
    if chat.state.pop(KEY, None) is not None:
        chat.save(update_fields=["state", "updated_at"])


def wanted(user: User) -> bool:
    """Botda so'rash kerakmi: guruh o'quvchisi, ismi tasdiqlanmagan yoki sanasi yo'q."""
    return person.needs_profile(user)


def later_button(locale: str) -> Rows:
    return [[button(t(locale, "btn_profile_later"), "pf:skip")]]


def begin(chat: BotChat, user: User, *, intro: bool = True, everything: bool = False) -> None:
    """To'ldirish boshlanadi: yetishmagan birinchi qadamdan (`everything` — hammasi qaytadan)."""
    if intro:
        send(chat.chat_id, t(chat.language, "profile_intro"))
    chat.state[KEY] = {"step": "", "at": int(time.time()), "all": everything}
    ask(chat, user, next_step(chat, user, after=None))


def next_step(chat: BotChat, user: User, *, after: str | None) -> str | None:
    if (current(chat) or {}).get("all"):
        index = ORDER.index(after) + 1 if after in ORDER else 0
        return ORDER[index] if index < len(ORDER) else None
    steps = person.missing(user)
    return steps[0] if steps else None


def ask(chat: BotChat, user: User, step: str | None) -> None:
    locale = chat.language
    if step is None:
        forget(chat)
        send(chat.chat_id, t(locale, "profile_done"))
        return
    remember(chat, step)
    if step == person.NAME:
        send(chat.chat_id, t(locale, "profile_ask_name"))
    elif step == person.BIRTH:
        send(chat.chat_id, t(locale, "profile_ask_birth"))
    else:
        send(chat.chat_id, t(locale, "profile_ask_photo"), later_button(locale))


def on_text(chat: BotChat, user: User, text: str) -> bool:
    """Profil kutayotgan matn (ism yoki sana). Qaytadi: matn shu yerda ishlandimi."""
    state = current(chat)
    step = (state or {}).get("step")
    locale = chat.language
    if step in (person.NAME, CONFIRM):
        name = person.parse_name(text)
        if name is None:
            send(chat.chat_id, t(locale, "profile_bad_name"))
            return True
        remember(chat, CONFIRM, name=[name.last, name.first, name.middle])
        rows: Rows = [
            [
                button(t(locale, "btn_profile_ok"), "pf:ok"),
                button(t(locale, "btn_profile_retry"), "pf:re"),
            ]
        ]
        check = t(
            locale,
            "profile_check_name",
            last=escape(name.last),
            first=escape(name.first),
            middle=escape(name.middle) or t(locale, "profile_empty"),
        )
        send(chat.chat_id, check, rows)
        return True
    if step == person.BIRTH:
        born = person.parse_birth(text)
        if born is None:
            send(chat.chat_id, t(locale, "profile_bad_birth"))
            return True
        person.save_birth(user, born)
        ask(chat, user, next_step(chat, user, after=person.BIRTH))
        return True
    if step == person.PHOTO:
        send(chat.chat_id, t(locale, "profile_only_photo"), later_button(locale))
        return True
    return False


def area(size: dict[str, Any]) -> int:
    return int(size.get("width") or 0) * int(size.get("height") or 0)


def image_of(message: dict[str, Any]) -> str:
    """Eng katta o'lcham (Telegram rasmni bir necha o'lchamda beradi) yoki rasm-fayl."""
    sizes = [item for item in message.get("photo") or [] if isinstance(item, dict)]
    if sizes:
        return str(max(sizes, key=area).get("file_id") or "")
    document = message.get("document")
    if isinstance(document, dict) and str(document.get("mime_type") or "").startswith("image/"):
        return str(document.get("file_id") or "")
    return ""


def on_media(chat: BotChat, user: User, message: dict[str, Any]) -> bool:
    """Selfi kutilayotgan bo'lsa — rasm saqlashga yuboriladi."""
    from .tasks import save_profile_photo

    if (current(chat) or {}).get("step") != person.PHOTO:
        return False
    file_id = image_of(message)
    if not file_id:
        send(chat.chat_id, t(chat.language, "profile_photo_bad"))
        return True
    send(chat.chat_id, t(chat.language, "profile_photo_wait"))
    chat_id, user_id = chat.chat_id, user.pk
    transaction.on_commit(lambda: save_profile_photo.delay(chat_id, user_id, file_id))
    return True


def store_photo(chat_id: int, user_id: int, file_id: str) -> None:
    """Celery: rasm Telegram'dan olinadi va kvadrat JPEG qilib saqlanadi."""
    chat = BotChat.objects.filter(chat_id=chat_id).first()
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if chat is None or user is None:
        return
    locale = chat.language or "uz"
    try:
        photos.set_avatar(user, telegram.download(file_id, limit=photos.MAX_BYTES))
    except (
        photos.PhotoError,
        telegram.TelegramError,
        telegram.TelegramNotConfiguredError,
        OSError,
    ) as exc:
        # Faqat xato turi: Telegram fayl havolasida bot tokeni bor.
        logger.warning("Profil rasmi saqlanmadi (user %s): %s", user_id, type(exc).__name__)
        send(chat_id, t(locale, "profile_photo_failed"), later_button(locale))
        return
    with transaction.atomic():
        chat = BotChat.objects.select_for_update().get(pk=chat.pk)
        if (current(chat) or {}).get("step") == person.PHOTO:
            forget(chat)
    send(chat_id, t(locale, "profile_done"))


def on_button(chat: BotChat, user: User, args: list[str]) -> str:
    """`pf:start|edit|photo|view|ok|re|skip`."""
    action = args[0] if args else ""
    state = current(chat)
    if action == "start":
        begin(chat, user, intro=False)
    elif action == "edit":
        begin(chat, user, intro=False, everything=True)
    elif action == "photo":
        chat.state[KEY] = {"step": "", "at": int(time.time()), "all": False}
        ask(chat, user, person.PHOTO)
    elif action == "view":
        show(chat, user)
    elif action == "ok":
        name = (state or {}).get("name")
        if state is None or not isinstance(name, list) or len(name) != 3:
            begin(chat, user, intro=False)  # eskirgan tugma: ism qaytadan so'raladi
        elif state.get("step") == CONFIRM:
            person.save_name(user, person.FullName(*(str(part) for part in name)))
            ask(chat, user, next_step(chat, user, after=person.NAME))
    elif action == "re":
        if state is None:
            chat.state[KEY] = {"step": "", "at": int(time.time()), "all": False}
        ask(chat, user, person.NAME)
    elif action == "skip":
        forget(chat)
        send(chat.chat_id, t(chat.language, "profile_later"))
    return ""


def show(chat: BotChat, user: User) -> None:
    """«👤 Profilim»: hozirgi ma'lumot, «O'zgartirish» va «Rasm yuborish»."""
    locale = chat.language
    empty = t(locale, "profile_empty")
    text = t(
        locale,
        "profile_view",
        last=escape(user.last_name) or empty,
        first=escape(user.first_name) or empty,
        middle=escape(user.middle_name) or empty,
        birth=user.birth_date.strftime("%d.%m.%Y") if user.birth_date else empty,
        photo=t(locale, "profile_photo_yes" if user.avatar else "profile_photo_no"),
    )
    rows: Rows = [
        [button(t(locale, "btn_profile_edit"), "pf:edit")],
        [button(t(locale, "btn_profile_photo"), "pf:photo")],
    ]
    send(chat.chat_id, text, rows)


def chat_of(user: User) -> BotChat | None:
    """O'quvchining bot chati (Telegram ulangan va bot bloklanmagan)."""
    uids = SocialAccount.objects.filter(
        user=user, provider=SocialAccount.Provider.TELEGRAM
    ).values_list("uid", flat=True)
    ids = [int(uid) for uid in uids if uid.isdigit()]
    return BotChat.objects.filter(chat_id__in=ids, blocked_at__isnull=True).first()


def push(user: User, *, once: bool = True) -> bool:
    """Botga «Profilni to'ldiring» taklifi (tugma bilan). `once` — oldin yuborilgan bo'lsa,
    qayta yuborilmaydi. Qaytadi: yuborildimi."""
    chat = chat_of(user)
    if chat is None or (once and chat.state.get(PUSHED)):
        return False
    locale = chat.language or user.locale or "uz"
    rows: Rows = [[button(t(locale, "btn_profile_start"), "pf:start")]]
    if not send(chat.chat_id, t(locale, "profile_push"), rows):
        return False
    with transaction.atomic():
        chat = BotChat.objects.select_for_update().get(pk=chat.pk)
        chat.state[PUSHED] = timezone.localdate().isoformat()
        chat.save(update_fields=["state", "updated_at"])
    return True
