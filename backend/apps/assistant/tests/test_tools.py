"""Vositalar: kurs ma'lumoti, kartochkalar va ariza (faqat mijoz bergan raqam bilan)."""

import json
from typing import Any
from unittest import mock

import pytest

from apps.assistant.models import Conversation
from apps.assistant.service import add_user_message
from apps.assistant.tools import run_tool
from apps.catalog.models import Course, Lesson, Module
from apps.leads.models import Lead

pytestmark = pytest.mark.django_db


def lead_input(**overrides: Any) -> dict[str, Any]:
    return {
        "phone": "‹telefon-1›",
        "name": "Aziz",
        "topic": "enrollment",
        "course_slug": "frontend",
        "study_format": "OFFLINE",
        "summary": "O'zi o'qiydi, kechqurun qulay",
        **overrides,
    }


def test_get_course_returns_program(conversation: Conversation, courses: list[Course]) -> None:
    course = courses[0]
    module = Module.objects.create(course=course, title_uz="HTML asoslari")
    Lesson.objects.create(module=module, title_uz="Birinchi sahifa", order=1)

    outcome = run_tool(conversation, "get_course", {"slug": "frontend"})

    data = json.loads(outcome.content)
    assert not outcome.is_error
    assert data["title"] == "Frontend dasturlash"
    assert data["program"] == [{"module": "HTML asoslari", "lessons": ["Birinchi sahifa"]}]
    assert "onlayn — 1 200 000 so'm, bir marta (umrbod kirish)" in data["prices"]


def test_get_course_unknown_or_draft(conversation: Conversation, courses: list[Course]) -> None:
    outcome = run_tool(conversation, "get_course", {"slug": "draft-kurs"})

    assert outcome.is_error
    assert "frontend" in outcome.content and "sifat-kids" in outcome.content


def test_show_courses_limits_and_orders(conversation: Conversation, courses: list[Course]) -> None:
    outcome = run_tool(
        conversation, "show_courses", {"slugs": ["sifat-kids", "frontend", "sifat-kids"]}
    )

    assert [card["slug"] for card in outcome.attachments] == ["sifat-kids", "frontend"]
    assert outcome.attachments[0]["price_offline_monthly"] == 450_000


def test_create_lead_from_masked_phone(conversation: Conversation, courses: list[Course]) -> None:
    add_user_message(conversation, "Men Aziz, +998 90 123 45 67")

    with mock.patch("apps.leads.services.notify_new_lead.delay"):
        outcome = run_tool(conversation, "create_lead", lead_input())

    assert not outcome.is_error
    lead = Lead.objects.get()
    assert (lead.phone, lead.name, lead.course) == ("+998901234567", "Aziz", courses[0])
    assert lead.source == Lead.Source.AI_WEB
    assert "[Kursga yozilish] O'zi o'qiydi" in lead.comment
    assert "Shakl: offlayn" in lead.comment
    assert f"/admin/assistant/conversation/{conversation.pk}/change/" in lead.comment
    conversation.refresh_from_db()
    assert conversation.lead == lead
    assert conversation.status == Conversation.Status.OPEN


def test_invented_phone_is_rejected(conversation: Conversation) -> None:
    add_user_message(conversation, "Qo'ng'iroq qiling")

    outcome = run_tool(conversation, "create_lead", lead_input(phone="+998 99 111 22 33"))

    assert outcome.is_error
    assert not Lead.objects.exists()


def test_complaint_needs_manager(conversation: Conversation) -> None:
    add_user_message(conversation, "Pul to'ladim, kurs ochilmadi. 90 123 45 67")

    with mock.patch("apps.leads.services.notify_new_lead.delay"):
        run_tool(conversation, "create_lead", lead_input(topic="student_issue", course_slug=""))

    conversation.refresh_from_db()
    assert conversation.status == Conversation.Status.MANAGER
    assert Lead.objects.get().comment.startswith("[O'quvchi muammosi]")


def test_repeated_lead_notifies_managers(conversation: Conversation) -> None:
    add_user_message(conversation, "90 123 45 67")
    Lead.objects.create(name="Aziz", phone="+998901234567")

    with mock.patch("apps.assistant.tasks.notify_managers.delay") as notify:
        run_tool(conversation, "create_lead", lead_input(course_slug=""))

    notify.assert_called_once_with(conversation.pk)
    assert Lead.objects.get().submissions == 2


def test_lead_calls_are_limited(conversation: Conversation) -> None:
    add_user_message(conversation, "90 123 45 67")
    conversation.context = {"lead_calls": 3}

    outcome = run_tool(conversation, "create_lead", lead_input(course_slug=""))

    assert outcome.is_error
    assert not Lead.objects.exists()


def test_unknown_tool_and_crash(conversation: Conversation) -> None:
    assert run_tool(conversation, "delete_everything", {}).is_error

    with mock.patch("apps.assistant.tools.published", side_effect=RuntimeError("db")):
        outcome = run_tool(conversation, "get_course", {"slug": "frontend"})
    assert outcome.is_error and "menejer" in outcome.content
