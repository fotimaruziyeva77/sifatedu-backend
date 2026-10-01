"""Tizim prompti faqat bazadagi faktlardan yig'iladi; o'zgaruvchan ma'lumot `<kontekst>`da."""

from datetime import datetime
from typing import Any

from django.utils import timezone

from apps.assistant.models import AssistantSettings, Conversation
from apps.assistant.prompt import build_system_prompt, context_block
from apps.catalog.models import Course
from apps.content.models import FAQItem, SiteSettings


def test_prompt_has_published_courses_prices_and_facts(courses: list[Course]) -> None:
    FAQItem.objects.create(question_uz="Sertifikat berasizmi?", answer_uz="Ha, kurs oxirida.")
    SiteSettings.objects.update_or_create(
        pk=1, defaults={"phone": "+998 71 200 00 00", "working_hours_uz": "Du–Sha 9:00–19:00"}
    )
    config = AssistantSettings.load()
    config.knowledge = "Birinchi dars bepul."
    config.save()

    prompt = build_system_prompt("uz")

    assert "frontend: «Frontend dasturlash»" in prompt
    assert "onlayn — 1 200 000 so'm, bir marta" in prompt
    assert "offlayn — 600 000 so'm oyiga" in prompt
    # Bolalar kursi faqat offlayn: onlayn narxi aytilmaydi.
    kids_line = next(line for line in prompt.splitlines() if line.startswith("- sifat-kids"))
    assert "7–11 yoshli bolalar" in kids_line
    assert "onlayn" not in kids_line
    assert "draft-kurs" not in prompt
    assert "Sertifikat berasizmi?" in prompt
    assert "Du–Sha 9:00–19:00" in prompt
    assert "Birinchi dars bepul." in prompt


def test_prompt_is_stable_for_cache(courses: list[Course]) -> None:
    # Vaqt yoki suhbatga bog'liq narsa yo'q: ketma-ket ikki so'rovda bir xil (kesh ishlaydi).
    assert build_system_prompt("uz") == build_system_prompt("uz")


def test_prompt_uses_conversation_language(courses: list[Course]) -> None:
    Course.objects.filter(slug="frontend").update(title_ru="Фронтенд-разработка")

    assert "«Фронтенд-разработка»" in build_system_prompt("ru")


def test_context_block(conversation: Conversation, db: Any) -> None:
    moment = timezone.make_aware(datetime(2026, 9, 28, 22, 14))
    conversation.name = "Aziz"
    conversation.phones = {"akkaunt": "+998901234567"}

    block = context_block(
        conversation,
        page="/uz/courses/frontend",
        quiz={"track": "Frontend", "level": ""},
        announce_user=True,
        now=moment,
    )

    assert block.startswith("<kontekst>\n") and block.endswith("\n</kontekst>")
    assert "vaqt: 2026-09-28 22:14, dushanba (Toshkent)" in block
    assert "kanal: sayt, sahifa: /uz/courses/frontend" in block
    assert "mijoz: saytga kirgan, ismi Aziz, raqami ‹telefon-akkaunt›" in block
    assert "kasb testi natijasi: track — Frontend" in block
    assert "+998" not in block
