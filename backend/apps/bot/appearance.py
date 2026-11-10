"""Bot ko'rinishi: buyruqlar, tavsif va qisqa tavsif (3 tilda). Logo va nom — BotFather'da."""

from apps.notifications import telegram
from apps.tenancy.access import has_feature
from apps.tenancy.sections import Feature
from apps.tenancy.sites import center_name, is_flagship, rebrand

COMMANDS = {
    "uz": [
        ("start", "Boshlash"),
        ("menu", "Menyu"),
        ("today", "Bugungi topshiriqlar"),
        ("tests", "Testlar"),
        ("schedule", "Jadval"),
        ("profile", "Profilim"),
        ("settings", "Sozlamalar"),
        ("help", "Yordam"),
    ],
    "ru": [
        ("start", "Начать"),
        ("menu", "Меню"),
        ("today", "Задания на сегодня"),
        ("tests", "Тесты"),
        ("schedule", "Расписание"),
        ("profile", "Мой профиль"),
        ("settings", "Настройки"),
        ("help", "Помощь"),
    ],
    "en": [
        ("start", "Start"),
        ("menu", "Menu"),
        ("today", "Today's tasks"),
        ("tests", "Quizzes"),
        ("schedule", "Schedule"),
        ("profile", "My profile"),
        ("settings", "Settings"),
        ("help", "Help"),
    ],
}
FLAGSHIP_INTRO = {
    "uz": "Sifat Edu — IT ta'lim platformasi.",
    "ru": "Sifat Edu — платформа IT-обучения.",
    "en": "Sifat Edu — an IT learning platform.",
}
INTRO = {
    "uz": "{name} — o'quv markazi boti.",
    "ru": "{name} — бот учебного центра.",
    "en": "{name} — the training center's bot.",
}
LINES = {
    "uz": (
        "📝 Dars testlari — shu yerda",
        "📅 Jonli darslar jadvali",
        "🔔 Yangiliklar va aksiyalar",
    ),
    "ru": (
        "📝 Тесты к урокам — здесь",
        "📅 Расписание живых занятий",
        "🔔 Новости и акции",
    ),
    "en": ("📝 Lesson quizzes — right here", "📅 Live class schedule", "🔔 News and offers"),
}
AI_LINE = {
    "uz": "💬 Savollarga AI maslahatchi javob beradi",
    "ru": "💬 На вопросы отвечает ИИ-консультант",
    "en": "💬 The AI advisor answers your questions",
}
OUTRO = {
    "uz": "Ro'yxatdan o'tish — bitta tugma, SMS kerak emas.",
    "ru": "Регистрация — одна кнопка, без SMS.",
    "en": "Sign up with one tap, no SMS needed.",
}
# Profil va ulashishda (120 belgigacha).
SHORT_DESCRIPTIONS = {
    "uz": "Sifat Edu: dars testlari, jadval va yangiliklar.",
    "ru": "Sifat Edu: тесты к урокам, расписание и новости.",
    "en": "Sifat Edu: lesson quizzes, schedule and news.",
}
DESCRIPTION_LIMIT = 512
SHORT_LIMIT = 120


def description(locale: str) -> str:
    """«Start» bosilishidan oldin ko'rinadi (512 belgigacha)."""
    intro = FLAGSHIP_INTRO[locale] if is_flagship() else INTRO[locale].format(name=center_name())
    lines = [*LINES[locale], *([AI_LINE[locale]] if has_feature(Feature.AI) else [])]
    return "\n\n".join((intro, "\n".join(lines), OUTRO[locale]))[:DESCRIPTION_LIMIT]


def apply_profile(*, token: str | None = None) -> None:
    """Telegram'ga yozadi. Xatoda istisno ko'taradi (`telegram.call` kabi)."""
    for locale, commands in COMMANDS.items():
        # O'zbekcha — standart (til aniqlanmaganlar ham shuni ko'radi).
        scope = {} if locale == "uz" else {"language_code": locale}
        telegram.call(
            "setMyCommands",
            {
                "commands": [{"command": name, "description": text} for name, text in commands],
                **scope,
            },
            token=token,
        )
        telegram.call(
            "setMyDescription", {"description": description(locale), **scope}, token=token
        )
        telegram.call(
            "setMyShortDescription",
            {"short_description": rebrand(SHORT_DESCRIPTIONS[locale])[:SHORT_LIMIT], **scope},
            token=token,
        )
