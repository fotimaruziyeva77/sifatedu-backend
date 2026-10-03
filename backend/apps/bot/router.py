"""Telegram bot: kelgan har bir yangilanishni (xabar, tugma, bot holati) kerakli joyga yuboradi.

Production'da Telegram webhook'ka yuboradi (`views.WebhookView` → Celery), local sinovda —
`manage.py telegram_poll`. Faqat shaxsiy chatlar: bot a'zo bo'lgan guruh va kanallardagi
xabarlar e'tiborsiz qoldiriladi (u yerdan faqat botning o'z holati — administrator qilindimi).

Yo'l: /start → til (bir marta) → majburiy obuna → "Telefonni yuborish" → menyu. Istalgan matn
(menyu tugmasi yoki yozma test javobi bo'lmasa) — AI maslahatchiga.
"""

import re
from typing import Any

from django.db import transaction
from django.utils import timezone, translation

from apps.core.phone import InvalidPhoneError, normalize_phone
from apps.notifications import linking, telegram
from apps.users.models import User

from . import (
    accounts,
    admin_panel,
    daily,
    exam,
    links,
    menu,
    placement,
    quiz,
    review,
    subscription,
    today,
)
from .models import BotChat
from .send import Rows, button, edit, escape, link, send
from .texts import CHOOSE_LANGUAGE, LANGUAGES, MENU_BY_LABEL, t

COMMANDS = {
    "/menu": "menu",
    "/help": "help",
    "/courses": "courses",
    "/tests": "tests",
    "/today": "today",
    "/schedule": "schedule",
    "/invite": "invite",
    "/settings": "settings",
    # Ochiq buyruqlar ro'yxatida yo'q: faqat statistikani ko'rish huquqi borlarga.
    "/admin": "admin",
}
QUIZ_BUTTONS = frozenset({"qa", "qt", "qd", "qo", "qm", "qr"})
# Saytdan bugungi kunlik testga: t.me/<bot>?start=dt
DAILY_START = "dt"
# Reklama manbasi: /start ig, /start tg, /start ads1 … (boshqa prefikslar — o'z ishlari).
SOURCE = re.compile(r"[a-z0-9_-]{1,32}")


def handle_update(update: dict[str, Any]) -> None:
    member = update.get("my_chat_member")
    if isinstance(member, dict):
        on_membership(member)
        return
    callback = update.get("callback_query")
    if isinstance(callback, dict):
        on_callback(callback)
        return
    message = update.get("message")
    if isinstance(message, dict):
        on_message(message)


# --- Umumiy ---


def touch(sender: dict[str, Any]) -> BotChat:
    """Botdagi odamni topadi yoki yozadi. Yozgan odam botni bloklamagan — belgi olinadi."""
    chat_id = sender["id"]
    profile = {
        "first_name": str(sender.get("first_name") or "")[:150],
        "username": str(sender.get("username") or "")[:64],
    }
    chat, _created = BotChat.objects.get_or_create(chat_id=chat_id, defaults=profile)
    changes: dict[str, Any] = {"last_seen_at": timezone.now(), "blocked_at": None}
    changes.update({key: value for key, value in profile.items() if getattr(chat, key) != value})
    BotChat.objects.filter(pk=chat.pk).update(**changes)
    for key, value in changes.items():
        setattr(chat, key, value)
    linking.set_blocked(chat_id, blocked=False)
    return chat


def locked(chat: BotChat) -> BotChat:
    """Bitta odamning ikki xabari parallel ishlanmasin (masalan, testda tez-tez bosilgan tugma)."""
    return BotChat.objects.select_for_update().get(pk=chat.pk)


def hello(first_name: str) -> str:
    return f", {escape(first_name)}" if first_name else ""


def ask_language(chat: BotChat) -> None:
    rows: Rows = [[button(label, f"lang:{code}") for code, label in LANGUAGES.items()]]
    send(chat.chat_id, CHOOSE_LANGUAGE, rows)


def subscribed(chat: BotChat, user: User | None) -> bool:
    """Majburiy kanallarga obuna bo'lganmi (xodimdan so'ralmaydi). Yo'q bo'lsa — so'raydi."""
    if user is not None and accounts.is_staff_account(user):
        return True
    lacking = subscription.missing(chat.chat_id)
    if not lacking:
        return True
    rows: Rows = [[link(channel.title, channel.url)] for channel in lacking]
    rows.append([button(t(chat.language, "btn_subscribed"), "sub")])
    send(chat.chat_id, t(chat.language, "subscribe"), rows)
    return False


def show_welcome(chat: BotChat, first_name: str) -> None:
    """Ro'yxatdan o'tmagan odam: nima qila olishi, telefon tugmasi va oferta."""
    locale = chat.language
    terms = t(
        locale,
        "terms",
        offer=links.site_url("/offer", locale),
        privacy=links.site_url("/privacy", locale),
    )
    send(
        chat.chat_id,
        f"{t(locale, 'welcome', name=hello(first_name))}\n\n{terms}",
        keyboard=menu.main_keyboard(locale, registered=False),
    )


def show_menu(chat: BotChat, user: User) -> None:
    send(
        chat.chat_id,
        t(chat.language, "welcome_back", name=hello(user.first_name)),
        keyboard=menu.main_keyboard(
            chat.language,
            registered=True,
            admin=admin_panel.allowed(user),
            newcomer=placement.offered(user),
        ),
    )


def need_account(chat: BotChat) -> None:
    send(
        chat.chat_id,
        t(chat.language, "need_account"),
        keyboard=menu.main_keyboard(chat.language, registered=False),
    )


def proceed(chat: BotChat, first_name: str) -> None:
    """Til tanlangach: obuna → ro'yxatdan o'tish yoki menyu → kutilayotgan ish (masalan, test)."""
    user = accounts.linked_user(chat.chat_id)
    if not subscribed(chat, user):
        return
    pending = str(chat.state.pop("start", "") or "")
    if pending:
        chat.save(update_fields=["state", "updated_at"])
    if user is None:
        show_welcome(chat, first_name)
        return
    show_menu(chat, user)
    if pending.startswith("quiz:") and pending[5:].isdigit():
        quiz.start(chat, user, int(pending[5:]))
    elif pending == DAILY_START:
        daily.entry(chat, user)


# --- /start ---


def start(chat: BotChat, sender: dict[str, Any], payload: str) -> None:
    user = accounts.linked_user(chat.chat_id)
    if payload.startswith(links.REFERRAL_PREFIX):
        if user is None:
            chat.referral_code = payload.removeprefix(links.REFERRAL_PREFIX)[:16]
            chat.source = chat.source or "ref"  # manbalar statistikasida — do'st taklifi
            chat.save(update_fields=["referral_code", "source", "updated_at"])
    elif linking.is_link_start(payload):
        # Kabinetdagi "Telegram'ni ulash": egalikni sayt (token) va Telegram (yozgan odam)
        # birga tasdiqlaydi.
        result = linking.link(payload, chat.chat_id)
        user = accounts.linked_user(chat.chat_id)
        adopt_language(chat, user)
        send(chat.chat_id, escape(linking.reply(result, chat.language or "uz")))
    elif payload.startswith(links.QUIZ_PREFIX):
        user = start_quiz_link(chat, sender, payload, user)
    elif payload == DAILY_START:
        # Saytdagi «Botda ishlash»: menyudan keyin bugungi kunlik test ochiladi.
        chat.state["start"] = DAILY_START
        chat.save(update_fields=["state", "updated_at"])
    elif SOURCE.fullmatch(payload.lower()) and not chat.source:
        # Birinchi manba saqlanadi (keyingi havolalar uni almashtirmaydi).
        chat.source = payload.lower()
        chat.save(update_fields=["source", "updated_at"])
    if not chat.language:
        ask_language(chat)
        return
    with translation.override(chat.language):
        proceed(chat, str(sender.get("first_name") or ""))


def adopt_language(chat: BotChat, user: User | None) -> None:
    """Saytdan kelgan odamga til qayta so'ralmaydi — saytdagi tili olinadi."""
    if user is not None and not chat.language:
        chat.language = user.locale or "uz"
        chat.save(update_fields=["language", "updated_at"])


def start_quiz_link(
    chat: BotChat, sender: dict[str, Any], payload: str, user: User | None
) -> User | None:
    """Saytdagi "Telegram'da ishlash": test botda boshlanadi. Telegram hali ulanmagan bo'lsa —
    shu akkauntga ulanadi (havolani saytga kirgan o'quvchining o'zi so'ragan)."""
    data = links.take_quiz(payload)
    owner_id = (data or {}).get("user")
    owner = (
        User.objects.filter(pk=owner_id, is_active=True).first()
        if isinstance(owner_id, int)
        else None
    )
    locale = chat.language or (owner.locale if owner else "uz")
    if data is None or owner is None:
        send(chat.chat_id, escape(linking.reply(linking.LinkResult.EXPIRED, locale)))
        return user
    if user is None:
        accounts.attach(owner, sender)
        user = owner
        send(chat.chat_id, escape(linking.reply(linking.LinkResult.LINKED, locale)))
    elif user.pk != owner.pk:
        send(chat.chat_id, escape(linking.reply(linking.LinkResult.TAKEN, locale)))
        return user
    adopt_language(chat, user)
    chat.state["start"] = f"quiz:{int(data['quiz'])}"
    chat.save(update_fields=["state", "updated_at"])
    return user


# --- Xabarlar ---


def on_message(message: dict[str, Any]) -> None:
    sender = message.get("from") or {}
    if (
        (message.get("chat") or {}).get("type") != "private"
        or sender.get("is_bot")
        or not isinstance(sender.get("id"), int)
    ):
        return
    chat = touch(sender)
    with transaction.atomic():
        chat = locked(chat)
        with translation.override(chat.language or "uz"):
            handle_message(chat, sender, message)


def handle_message(chat: BotChat, sender: dict[str, Any], message: dict[str, Any]) -> None:
    text = str(message.get("text") or "").strip()
    if text.startswith("/start"):
        start(chat, sender, text.removeprefix("/start").strip())
        return
    if not chat.language:
        ask_language(chat)
        return
    user = accounts.linked_user(chat.chat_id)
    if not subscribed(chat, user):
        return
    contact = message.get("contact")
    if isinstance(contact, dict):
        on_contact(chat, sender, contact, user)
        return
    command = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
    action = COMMANDS.get(command) or MENU_BY_LABEL.get(text)
    if action:
        run_menu(chat, user, action)
        return
    if (
        user is not None
        and text
        and (
            quiz.on_text(chat, user, text)
            or exam.on_text(chat, user, text)
            or review.on_text(chat, user, text)
            or placement.on_text(chat, user, text)
            or daily.on_text(chat, user, text)
        )
    ):
        return
    if not text:
        send(chat.chat_id, t(chat.language, "only_text"))
        return
    ask_ai(chat, sender, text)


def run_menu(chat: BotChat, user: User | None, action: str) -> None:
    locale = chat.language
    if action == "help":
        send(chat.chat_id, t(locale, "help"))
    elif action == "ask":
        send(chat.chat_id, t(locale, "ask"))
    elif action == "settings":
        menu.settings(chat, user)
    elif action == "admin":
        admin_panel.show(chat, user)
    elif user is None:
        need_account(chat)
    elif action == "menu":
        show_menu(chat, user)
    elif action == "courses":
        menu.courses(chat, user)
    elif action == "tests":
        menu.tests(chat, user)
    elif action == "today":
        today.show(chat, user)
    elif action == "placement":
        placement.choose(chat, user)
    elif action == "schedule":
        menu.schedule(chat, user)
    elif action == "invite":
        menu.invite(chat, user)


def on_contact(
    chat: BotChat, sender: dict[str, Any], contact: dict[str, Any], user: User | None
) -> None:
    locale = chat.language
    # Faqat o'z raqami: boshqa odamning kontakti bilan akkaunt ochib (yoki egallab) bo'lmaydi.
    if contact.get("user_id") != sender.get("id"):
        send(chat.chat_id, t(locale, "not_own"))
        return
    try:
        phone = normalize_phone(str(contact.get("phone_number") or ""))
    except InvalidPhoneError:
        send(chat.chat_id, t(locale, "only_uz"))
        return
    if user is not None:
        # Saytdagi havola bilan ulangan Telegram raqamini tasdiqladi: parolsiz kirish ochiladi.
        if phone == user.phone and chat.verified_phone != phone:
            chat.verified_phone = phone
            chat.save(update_fields=["verified_phone", "updated_at"])
        show_menu(chat, user)
        return
    outcome, account = accounts.register(phone, sender, locale, chat.referral_code)
    if account is None:
        key = "staff_contact" if outcome == accounts.Outcome.STAFF else "account_blocked"
        send(chat.chat_id, t(locale, key))
        return
    chat.referral_code = ""
    chat.verified_phone = phone
    chat.save(update_fields=["referral_code", "verified_phone", "updated_at"])
    if outcome == accounts.Outcome.CREATED and chat.source and not account.signup_source:
        account.signup_source = chat.source
        account.save(update_fields=["signup_source"])
    text = (
        t(locale, "registered")
        if outcome == accounts.Outcome.CREATED
        else t(locale, "linked", name=hello(account.first_name))
    )
    newcomer = placement.offered(account)
    keyboard = menu.main_keyboard(locale, registered=True, newcomer=newcomer)
    send(chat.chat_id, text, keyboard=keyboard)
    site = link(t(locale, "btn_site"), links.login_url(account, "/dashboard", chat))
    send(chat.chat_id, t(locale, "site_hint"), [[site]])
    if newcomer:
        # Yangi kelgan: darhol yo'nalish va bepul daraja testi (kupon bilan).
        placement.choose(chat, account)


def ask_ai(chat: BotChat, sender: dict[str, Any], text: str) -> None:
    """Savol — AI maslahatchiga (alohida navbatda: javob 5–20 soniya, bot tugmalari kutmasin)."""
    from apps.assistant.tasks import telegram_answer

    profile = {
        key: str(sender.get(key) or "")[:64] for key in ("first_name", "last_name", "username")
    }
    language = chat.language or "uz"
    chat_id = chat.chat_id
    transaction.on_commit(lambda: telegram_answer.delay(chat_id, profile, text, language))


# --- Tugmalar ---


def on_callback(callback: dict[str, Any]) -> None:
    sender = callback.get("from") or {}
    message = callback.get("message") or {}
    callback_id = str(callback.get("id") or "")
    if (message.get("chat") or {}).get("type") != "private" or not isinstance(
        sender.get("id"), int
    ):
        telegram.answer_callback(callback_id)
        return
    chat = touch(sender)
    with transaction.atomic():
        chat = locked(chat)
        with translation.override(chat.language or "uz"):
            notice = handle_callback(chat, sender, str(callback.get("data") or ""), message)
    telegram.answer_callback(callback_id, notice, alert=bool(notice))


def handle_callback(
    chat: BotChat, sender: dict[str, Any], data: str, message: dict[str, Any]
) -> str:
    """Tugma bosildi. Qaytadi: qisqa ogohlantirish (bo'sh — kerak emas)."""
    action, _, rest = data.partition(":")
    args = rest.split(":") if rest else []
    first_name = str(sender.get("first_name") or "")
    if action == "lang":
        if not args or args[0] not in LANGUAGES:
            ask_language(chat)
            return ""
        chat.language = args[0]
        chat.save(update_fields=["language", "updated_at"])
        edit(chat.chat_id, message.get("message_id"), f"✅ {LANGUAGES[chat.language]}")
        with translation.override(chat.language):
            proceed(chat, first_name)
        return ""
    if action == "sub":
        if subscription.missing(chat.chat_id, fresh=True):
            return t(chat.language, "not_subscribed")
        proceed(chat, first_name)
        return ""
    if action in ("news", "mute"):
        chat.news = False if action == "mute" else not chat.news
        chat.save(update_fields=["news", "updated_at"])
        if action == "news":
            user = accounts.linked_user(chat.chat_id)
            text, rows = menu.settings_view(chat, user)
            edit(chat.chat_id, message.get("message_id"), text, rows)
        return t(chat.language, "news_enabled" if chat.news else "news_muted")
    user = accounts.linked_user(chat.chat_id)
    if action == "ad":
        # Admin panel: davr yoki «Yangilash» (huquq ichida tekshiriladi).
        return admin_panel.on_button(chat, user, args, message.get("message_id"))
    if user is None:
        need_account(chat)
        return ""
    if action in ("qs", "qn") and args and args[0].isdigit():
        if subscribed(chat, user):
            quiz.start(chat, user, int(args[0]), fresh=action == "qn")
        return ""
    if action in ("xs", "xg") and args and args[0].isdigit():
        # Oylik imtihon: "xs" — shartlar va "Boshlash", "xg" — boshlash yoki davom ettirish.
        if subscribed(chat, user):
            (exam.intro if action == "xs" else exam.start)(chat, user, int(args[0]))
        return ""
    if action == "dt":
        today.show(chat, user)
        return ""
    if action in ("pt", "pg") and args and args[0].isdigit():
        # Daraja testi: "pt" — shartlar va "Boshlash", "pg" — boshlash yoki davom ettirish.
        if subscribed(chat, user):
            (placement.intro if action == "pt" else placement.start)(chat, user, int(args[0]))
        return ""
    if action in ("dq", "dg", "dr", "dv"):
        # Kunlik test: "dq" — bugungi (shartlar yoki davomi), "dg" — boshlash, "dr" — guruh
        # reytingi, "dv" — javoblar va izohlar (test yopilgach).
        if not subscribed(chat, user):
            return ""
        number = int(args[0]) if args and args[0].isdigit() else None
        if action == "dq":
            daily.entry(chat, user)
        elif number is not None:
            {"dg": daily.start, "dr": daily.rating, "dv": daily.review}[action](chat, user, number)
        return ""
    if action == "rv":
        # Kunlik topshiriq: o'tilgan testlardan 5 savol.
        if subscribed(chat, user):
            review.start(chat, user)
        return ""
    if action in QUIZ_BUTTONS:
        if exam.is_exam(chat):
            return exam.on_button(chat, user, action, args)
        if placement.is_placement(chat):
            return placement.on_button(chat, user, action, args)
        if daily.is_daily(chat):
            return daily.on_button(chat, user, action, args)
        if review.is_review(chat):
            return review.on_button(chat, user, action, args)
        return quiz.on_button(chat, user, action, args)
    return ""


# --- Bot holati ---


def on_membership(member: dict[str, Any]) -> None:
    """Foydalanuvchi botni blokladi yoki qaytdi: xabarlar shunga qarab yuboriladi. Kanal yoki
    guruh bo'lsa — bot u yerda administratormi (majburiy obuna uchun kanal ID si)."""
    chat = member.get("chat") or {}
    chat_id = chat.get("id")
    status = str((member.get("new_chat_member") or {}).get("status") or "")
    if chat.get("type") in ("channel", "group", "supergroup"):
        subscription.remember(chat, status)
        return
    if chat.get("type") != "private" or not isinstance(chat_id, int):
        return
    blocked = status == "kicked"
    BotChat.objects.filter(chat_id=chat_id).update(blocked_at=timezone.now() if blocked else None)
    linking.set_blocked(chat_id, blocked=blocked)
