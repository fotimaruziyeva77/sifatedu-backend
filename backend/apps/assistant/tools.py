"""Agent vositalari (Gemini function calling): kurs ma'lumoti, chatdagi kartochkalar va ariza.

Vositalar faqat ommaviy ma'lumotni o'qiydi va ariza yaratadi — AI hech qanday shaxsiy ma'lumotni
o'qiy olmaydi. Natija modelga JSON matn bo'lib qaytadi; xatoda — nima qilish kerakligi yoziladi.
Model kiritmani sxemaga to'liq moslamasligi mumkin — har bir vosita kiritmani o'zi tekshiradi
(turi, ruxsat etilgan qiymatlar).
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.db.models import Prefetch, QuerySet
from django.urls import reverse
from django.utils import translation

from apps.catalog.models import Course, Lesson, Module
from apps.content.models import SiteSettings
from apps.leads.models import Lead
from apps.leads.services import LeadInput, submit_lead

from .models import Conversation
from .phones import resolve
from .prompt import course_facts

logger = logging.getLogger(__name__)

MAX_CARDS = 3
MAX_LEAD_CALLS = 3
TOPICS = {
    "enrollment": "Kursga yozilish",
    "question": "Javobsiz savol",
    "complaint": "Shikoyat",
    "student_issue": "O'quvchi muammosi",
}
FORMATS = {"ONLINE": "onlayn", "OFFLINE": "offlayn"}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_course",
        "description": (
            "Bitta kurs haqida to'liq ma'lumot: kimga mo'ljallangan, daraja, narxlar, davomiylik, "
            "modullar va darslar ro'yxati, ustozlar, tavsif. Mijoz kurs dasturi, nimalarni "
            "o'rganishi, ustozlar yoki davomiylik haqida so'raganda ishlat. Kurslar ro'yxati va "
            "asosiy narxlar tizim promptida bor — faqat shu uchun chaqirma."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "slug": {
                    "type": "string",
                    "description": "Kurs slug'i tizim promptidagi ro'yxatdan, masalan frontend",
                }
            },
            "required": ["slug"],
            "additionalProperties": False,
        },
    },
    {
        "name": "show_courses",
        "description": (
            "Mijozga chat ichida kurs kartochkalarini ko'rsatadi: nomi, narxi va kurs sahifasiga "
            "havola. Kurs tavsiya qilganingda yoki mijoz kurslarni ko'rmoqchi bo'lganda ishlat — "
            "1 tadan 3 tagacha eng mos kurs. Kartochka chiqqach, matningda havola yozish "
            "shart emas."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "slugs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Kurs slug'lari, eng mosi birinchi",
                }
            },
            "required": ["slugs"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_lead",
        "description": (
            "Menejerlarga ariza qoldiradi: menejer ish vaqtida mijozga qo'ng'iroq qiladi. Mijoz "
            "telefon raqamini bergandan keyingina chaqir. Mavzular: enrollment — kursga yozilish "
            "yoki bepul maslahat; question — sen javob bera olmagan savol; complaint — shikoyat; "
            "student_issue — mavjud o'quvchining muammosi (to'lov, kirish). Muvaffaqiyatli bo'lsa, "
            "mijozga ariza qabul qilinganini va menejer qachon qo'ng'iroq qilishini ayt."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "phone": {
                    "type": "string",
                    "description": (
                        "Mijoz raqamining belgisi, masalan ‹telefon-1› yoki ‹telefon-akkaunt›"
                    ),
                },
                "name": {
                    "type": "string",
                    "description": "Mijozning ismi; bilmasang — bo'sh qator",
                },
                "topic": {"type": "string", "enum": list(TOPICS)},
                "course_slug": {
                    "type": "string",
                    "description": "Qiziqqan kurs slug'i; aniq bo'lmasa — bo'sh qator",
                },
                "study_format": {"type": "string", "enum": ["ONLINE", "OFFLINE", "UNKNOWN"]},
                "summary": {
                    "type": "string",
                    "description": (
                        "Menejer uchun 1–3 jumla: kim o'qiydi, nimaga qiziqdi, qanday savol yoki "
                        "muammo, qachon qo'ng'iroq qilish qulay. O'zbek tilida."
                    ),
                },
            },
            "required": ["phone", "topic", "summary"],
            "additionalProperties": False,
        },
    },
]


@dataclass
class ToolOutcome:
    """Vosita natijasi: modelga matn, chatga (ixtiyoriy) kurs kartochkalari."""

    content: str
    is_error: bool = False
    attachments: list[dict[str, Any]] = field(default_factory=list)


def ok(data: dict[str, Any], attachments: list[dict[str, Any]] | None = None) -> ToolOutcome:
    return ToolOutcome(json.dumps(data, ensure_ascii=False), attachments=attachments or [])


def error(message: str) -> ToolOutcome:
    return ToolOutcome(message, is_error=True)


def published() -> QuerySet[Course]:
    return Course.objects.filter(status=Course.Status.PUBLISHED)


def available_slugs() -> str:
    return ", ".join(published().order_by("order", "id").values_list("slug", flat=True))


def course_card(course: Course) -> dict[str, Any]:
    """Chatdagi kartochka (frontend va Telegram uni ko'rsatadi)."""
    return {
        "slug": course.slug,
        "title": course.title,
        "icon": course.icon,
        "audience": course.audience,
        "age_min": course.age_min,
        "age_max": course.age_max,
        "study_format": course.study_format,
        "is_free": course.is_free,
        "price_online": course.price_online,
        "price_offline_monthly": course.price_offline_monthly,
        "duration_hours": course.duration_hours,
        "lesson_count": course.lesson_count,
    }


def get_course(conversation: Conversation, data: dict[str, Any]) -> ToolOutcome:
    slug = str(data.get("slug", "")).strip()
    lessons = Lesson.objects.order_by("order", "id")
    modules = Module.objects.order_by("order", "id").prefetch_related(
        Prefetch("lessons", queryset=lessons)
    )
    with translation.override(conversation.locale):
        course = (
            published()
            .prefetch_related(Prefetch("modules", queryset=modules), "instructors")
            .filter(slug=slug)
            .first()
        )
        if course is None:
            return error(f"Bunday kurs yo'q: {slug!r}. Mavjud slug'lar: {available_slugs()}.")
        return ok(course_facts(course))


def show_courses(conversation: Conversation, data: dict[str, Any]) -> ToolOutcome:
    raw = data.get("slugs")
    slugs = (
        [str(slug).strip() for slug in raw if str(slug).strip()] if isinstance(raw, list) else []
    )
    slugs = list(dict.fromkeys(slugs))[:MAX_CARDS]
    with translation.override(conversation.locale):
        found = {course.slug: course for course in published().filter(slug__in=slugs)}
        cards = [course_card(found[slug]) for slug in slugs if slug in found]
    missing = [slug for slug in slugs if slug not in found]
    if not cards:
        return error(f"Kurs topilmadi: {slugs}. Mavjud slug'lar: {available_slugs()}.")
    result: dict[str, Any] = {"shown": [card["title"] for card in cards]}
    if missing:
        result["not_found"] = missing
    return ok(result, attachments=cards)


def admin_link(conversation: Conversation) -> str:
    path = reverse("admin:assistant_conversation_change", args=[conversation.pk])
    return f"{settings.APP_URL.rstrip('/')}{path}"


def create_lead(conversation: Conversation, data: dict[str, Any]) -> ToolOutcome:
    phone = resolve(str(data.get("phone", "")), conversation.phones)
    if phone is None:
        return error(
            "Raqam topilmadi. Mijozdan telefon raqamini yozishini so'ra; keyin create_lead'ga "
            "u yozgan raqamning ‹telefon-N› belgisini ber."
        )
    calls = int(conversation.context.get("lead_calls", 0))
    if calls >= MAX_LEAD_CALLS:
        return error("Bu suhbatdan ariza allaqachon yuborilgan. Mijozga menejer bog'lanishini ayt.")

    topic = str(data.get("topic", "enrollment"))
    topic = topic if topic in TOPICS else "enrollment"
    summary = " ".join(str(data.get("summary", "")).split())[:600]
    name = " ".join(str(data.get("name", "")).split())[:100]
    name = name or conversation.name or "Mijoz (AI chat)"
    course = published().filter(slug=str(data.get("course_slug", "")).strip()).first()
    study_format = FORMATS.get(str(data.get("study_format", "")))

    comment = "\n".join(
        line
        for line in (
            f"[{TOPICS[topic]}] {summary}",
            f"Shakl: {study_format}" if study_format else "",
            f"AI suhbat: {admin_link(conversation)}",
        )
        if line
    )
    source = (
        Lead.Source.AI_TELEGRAM
        if conversation.channel == Conversation.Channel.TELEGRAM
        else Lead.Source.AI_WEB
    )
    lead, created = submit_lead(
        LeadInput(
            name=name,
            phone=phone,
            course=course,
            comment=comment,
            locale=conversation.locale,
            source_page=conversation.source_page[:500],
            source=source,
        )
    )

    conversation.lead = lead
    conversation.name = conversation.name or name
    conversation.summary = summary
    conversation.context = {**conversation.context, "lead_calls": calls + 1}
    fields = ["lead", "name", "summary", "context", "updated_at"]
    if topic != "enrollment":
        conversation.status = Conversation.Status.MANAGER
        fields.append("status")
    conversation.save(update_fields=fields)

    if not created:
        # Takroriy ariza birlashtirildi — menejerlar yangi murojaatni ham bilishi kerak.
        from .tasks import notify_managers

        notify_managers.delay(conversation.pk)

    site = SiteSettings.load()
    return ok(
        {
            "saved": True,
            "manager_working_hours": site.working_hours or None,
            "next_step": "Menejer ish vaqtida shu raqamga qo'ng'iroq qiladi.",
        }
    )


HANDLERS: dict[str, Callable[[Conversation, dict[str, Any]], ToolOutcome]] = {
    "get_course": get_course,
    "show_courses": show_courses,
    "create_lead": create_lead,
}


def run_tool(conversation: Conversation, name: str, data: dict[str, Any]) -> ToolOutcome:
    handler = HANDLERS.get(name)
    if handler is None:
        return error(f"Bunday vosita yo'q: {name}.")
    try:
        return handler(conversation, data if isinstance(data, dict) else {})
    except Exception:
        logger.exception("AI vositasi ishlamadi: %s", name)
        return error(
            "Vosita vaqtincha ishlamadi. Mijozga menejer bog'lanishini ayt va raqamini so'ra."
        )
