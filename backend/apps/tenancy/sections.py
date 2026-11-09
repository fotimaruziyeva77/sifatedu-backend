"""Tarifga bog'langan bo'limlar va ular qaysi kodga tegishli.

Asos (o'quvchilar, guruhlar, jadval, davomat, arizalar, sayt, katalog) hamma tarifda ochiq, shuning
uchun bu ro'yxatda yo'q. Tarif mazmuni kodda emas — platforma panelida (`tenancy.Plan`).
"""

from collections.abc import Iterable
from typing import Any

from django.db import models


class Feature(models.TextChoices):
    LESSONS = "lessons", "Dars testlari, uy vazifasi, slaydlar"
    EXAMS = "exams", "Kunlik test, oylik imtihon, sertifikat"
    PLACEMENT = "placement", "Daraja testi va kuponlar"
    REWARDS = "rewards", "XP, reyting, do'kon"
    AI = "ai", "AI maslahatchi va AI test"
    VIDEO = "video", "Video darslar"
    BOT = "bot", "Telegram bot, xabarnomalar, SMS"
    CLICK = "click", "Click orqali online to'lov"


# Savollar bankidan foydalanadi: darslar bo'limisiz ishlamaydi.
REQUIRES: dict[str, str] = {
    Feature.EXAMS: Feature.LESSONS,
    Feature.PLACEMENT: Feature.LESSONS,
    Feature.AI: Feature.LESSONS,
}
# Butun ilova bitta bo'limga tegishli.
APP_FEATURES: dict[str, str] = {
    "quizzes": Feature.LESSONS,
    "homework": Feature.LESSONS,
    "dailytest": Feature.EXAMS,
    "exams": Feature.EXAMS,
    "certificates": Feature.EXAMS,
    "placement": Feature.PLACEMENT,
    "rewards": Feature.REWARDS,
    "shop": Feature.REWARDS,
    "assistant": Feature.AI,
    "videos": Feature.VIDEO,
    "bot": Feature.BOT,
    "payments": Feature.CLICK,
}
# Ilovaning bir qismi boshqacha: `ilova.model` — shu bo'limlardan biri ochiq bo'lsa, ochiq.
MODEL_FEATURES: dict[str, tuple[str, ...]] = {
    "catalog.lessonslides": (Feature.LESSONS,),
    "quizzes.quizdraft": (Feature.AI,),
    "rewards.coupon": (Feature.PLACEMENT, Feature.REWARDS),
    # O'yin sozlamalarida kunlik test va daraja testi qiymatlari ham bor.
    "rewards.gamesettings": (Feature.REWARDS, Feature.EXAMS, Feature.PLACEMENT),
}
TASK_FEATURES: dict[str, str] = {"apps.quizzes.tasks.generate_draft": Feature.AI}
# Tarif va holatdan qat'i nazar: boshlangan to'lov tugaydi, shaxsiy ma'lumot anonimlashadi.
ALWAYS_RUN_TASKS = frozenset(
    {
        "apps.assistant.tasks.anonymize_old_conversations",
        "apps.payments.tasks.expire_orders",
        "apps.payments.tasks.finish_payment",
    }
)


def with_dependencies(features: Iterable[str]) -> frozenset[str]:
    found = set(features)
    return frozenset(found | {REQUIRES[item] for item in found if item in REQUIRES})


def _of_module(module: str) -> str | None:
    """`apps.<ilova>.…` nomidan."""
    parts = module.split(".")
    return APP_FEATURES.get(parts[1]) if parts[0] == "apps" and len(parts) > 1 else None


def view_target(view: Any) -> Any:
    """`as_view()` natijasidan ko'rinish klassi (funksiya bo'lsa — o'zi)."""
    return getattr(view, "cls", None) or getattr(view, "view_class", None) or view


def feature_of_view(view: Any) -> str | None:
    """Ko'rinish qaysi bo'limga tegishli: `feature` atributi (None — doim ochiq) yoki ilovasi."""
    target = view_target(view)
    if hasattr(target, "feature"):
        return str(target.feature) if target.feature else None
    return _of_module(target.__module__)


def feature_of_task(name: str) -> str | None:
    return TASK_FEATURES.get(name) or _of_module(name)


def features_of_perm(perm: str) -> tuple[str, ...]:
    """`ilova.amal_model` ruxsati: shu bo'limlardan biri ochiq bo'lishi kerak (bo'sh — asos)."""
    app_label, _dot, codename = perm.partition(".")
    model = f"{app_label}.{codename.partition('_')[2]}"
    if model in MODEL_FEATURES:
        return MODEL_FEATURES[model]
    feature = APP_FEATURES.get(app_label)
    return (feature,) if feature else ()


def features_of_app(app_label: str) -> tuple[str, ...]:
    """Ilova admin menyusida ko'rinadimi: o'zining yoki bironta modelining bo'limi ochiq."""
    own = APP_FEATURES.get(app_label)
    if own is None:
        return ()
    extra = (
        feature
        for model, features in MODEL_FEATURES.items()
        if model.startswith(f"{app_label}.")
        for feature in features
    )
    return (own, *extra)
