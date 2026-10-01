"""Bot ko'rinishi: buyruqlar menyusi, tavsif va qisqa tavsif (3 tilda).

Yangi bot tokeni berilganda (yoki matn o'zgarganda) bir marta ishga tushiriladi:
`python manage.py bot_setup`. Logo va bot nomi BotFather'da qo'yiladi.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.notifications import telegram

COMMANDS = {
    "uz": [
        ("start", "Boshlash"),
        ("menu", "Menyu"),
        ("today", "Bugungi topshiriqlar"),
        ("tests", "Testlar"),
        ("schedule", "Jadval"),
        ("settings", "Sozlamalar"),
        ("help", "Yordam"),
    ],
    "ru": [
        ("start", "Начать"),
        ("menu", "Меню"),
        ("today", "Задания на сегодня"),
        ("tests", "Тесты"),
        ("schedule", "Расписание"),
        ("settings", "Настройки"),
        ("help", "Помощь"),
    ],
    "en": [
        ("start", "Start"),
        ("menu", "Menu"),
        ("today", "Today's tasks"),
        ("tests", "Quizzes"),
        ("schedule", "Schedule"),
        ("settings", "Settings"),
        ("help", "Help"),
    ],
}
# "Start" bosilishidan oldin ko'rinadi (512 belgigacha).
DESCRIPTIONS = {
    "uz": (
        "Sifat Edu — IT ta'lim platformasi.\n\n"
        "📝 Dars testlari — shu yerda\n📅 Jonli darslar jadvali\n🔔 Yangiliklar va aksiyalar\n"
        "💬 Savollarga AI maslahatchi javob beradi\n\n"
        "Ro'yxatdan o'tish — bitta tugma, SMS kerak emas."
    ),
    "ru": (
        "Sifat Edu — платформа IT-обучения.\n\n"
        "📝 Тесты к урокам — здесь\n📅 Расписание живых занятий\n🔔 Новости и акции\n"
        "💬 На вопросы отвечает ИИ-консультант\n\n"
        "Регистрация — одна кнопка, без SMS."
    ),
    "en": (
        "Sifat Edu — an IT learning platform.\n\n"
        "📝 Lesson quizzes — right here\n📅 Live class schedule\n🔔 News and offers\n"
        "💬 The AI advisor answers your questions\n\n"
        "Sign up with one tap, no SMS needed."
    ),
}
# Profil va ulashishda (120 belgigacha).
SHORT_DESCRIPTIONS = {
    "uz": "Sifat Edu: dars testlari, jadval, yangiliklar va AI maslahatchi.",
    "ru": "Sifat Edu: тесты к урокам, расписание, новости и ИИ-консультант.",
    "en": "Sifat Edu: lesson quizzes, schedule, news and an AI advisor.",
}


class Command(BaseCommand):
    help = "Bot buyruqlari va tavsifini Telegram'ga yozadi (3 tilda)."

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            for locale in COMMANDS:
                # O'zbekcha — standart (til aniqlanmaganlar ham shuni ko'radi).
                scope = {} if locale == "uz" else {"language_code": locale}
                commands = [
                    {"command": command, "description": description}
                    for command, description in COMMANDS[locale]
                ]
                telegram.call("setMyCommands", {"commands": commands, **scope})
                telegram.call("setMyDescription", {"description": DESCRIPTIONS[locale], **scope})
                telegram.call(
                    "setMyShortDescription",
                    {"short_description": SHORT_DESCRIPTIONS[locale], **scope},
                )
        except telegram.TelegramNotConfiguredError as exc:
            raise CommandError("TELEGRAM_BOT_TOKEN bo'sh.") from exc
        except (OSError, telegram.TelegramError) as exc:
            raise CommandError(f"Telegram javob bermadi: {exc}") from exc
        self.stdout.write(self.style.SUCCESS("Bot buyruqlari va tavsifi yozildi (uz, ru, en)."))
