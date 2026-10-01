"""Botda dars testi: 5 turdagi savol, faqat ✅/❌, natija, xatolar ustida ishlash, qulflar."""

from typing import Any

import pytest

from apps.bot.models import BotChat
from apps.bot.router import handle_update
from apps.learning import access
from apps.live import services as live
from apps.live.models import GroupLesson
from apps.notifications.models import Notification
from apps.quizzes.models import Attempt, Question, Quiz
from apps.quizzes.parser import parse
from apps.quizzes.services import Layout, import_questions

from .conftest import APP, TG_ID, FakeTelegram, World, buttons, connect, message, press

pytestmark = pytest.mark.django_db

STEPS = ["HTML o'qiladi", "CSS qo'llanadi", "JavaScript ishga tushadi"]
PAIRS = {"HTML": "tuzilma", "CSS": "ko'rinish", "JavaScript": "harakat"}


def state() -> dict[str, Any]:
    return dict(BotChat.objects.get(chat_id=TG_ID).state.get("quiz") or {})


def current() -> tuple[str, Layout]:
    now = state()
    attempt = Attempt.objects.get(pk=now["a"])
    question = Question.objects.get(pk=now["q"])
    return f"{attempt.pk}:{question.pk}", Layout.build(question, attempt.seed)


def spot(layout: Layout, text: str, *, match: bool = False) -> int:
    values = [item.match if match else item.text for item in layout.shown]
    return values.index(text) + 1


def answer(*, right: bool = True) -> None:
    """Joriy savolga tugmalar (yoki matn) bilan javob beradi."""
    ref, layout = current()
    kind = layout.question.kind
    if kind == Question.Kind.SINGLE:
        text = "HyperText Markup Language" if right else "High Tech Modern Language"
        handle_update(press(f"qa:{ref}:{spot(layout, text)}"))
    elif kind == Question.Kind.MULTIPLE:
        for text in ["<div>", "<p>"] if right else ["<div>"]:
            handle_update(press(f"qt:{ref}:{spot(layout, text)}"))
        handle_update(press(f"qd:{ref}"))
    elif kind == Question.Kind.TEXT:
        handle_update(message("H1." if right else "h2"))
    elif kind == Question.Kind.ORDER:
        for text in STEPS if right else reversed(STEPS):
            handle_update(press(f"qo:{ref}:{spot(layout, text)}"))
    else:
        rights = [PAIRS[item.text] for item in layout.choices]
        if not right:
            rights[0], rights[1] = rights[1], rights[0]
        for text in rights:
            handle_update(press(f"qm:{ref}:{spot(layout, text, match=True)}"))


def play(tg: FakeTelegram, world: World, wrong: set[str] | frozenset[str] = frozenset()) -> None:
    handle_update(press(f"qs:{world.quiz.pk}"))
    for kind in ("SINGLE", "MULTIPLE", "TEXT", "ORDER", "MATCH"):
        assert Question.objects.get(pk=state()["q"]).kind == kind
        answer(right=kind not in wrong)


def test_quiz_passes_in_bot_and_opens_next_lesson(tg: FakeTelegram, world: World) -> None:
    connect(world.student)
    assert not access.can_open_lesson(world.student, world.lessons[1])

    play(tg, world)

    intro = tg.messages[0]["text"]
    assert "HTML asoslari" in intro and "5 ta savol" in intro and "70%" in intro
    verdicts = [edit["text"] for edit in tg.edits if "Javobingiz" in edit["text"]]
    assert len(verdicts) == 5 and all(text.endswith("✅ To'g'ri") for text in verdicts)
    result = tg.last
    assert "Test topshirildi" in result["text"] and "100% (5/5) ⭐⭐⭐" in result["text"]
    assert "Barcha javoblar to'g'ri" in result["text"]
    [next_lesson] = buttons(result)
    assert next_lesson["text"] == "▶️ Keyingi darsga"
    assert next_lesson["url"].startswith(f"{APP}/api/v1/bot/login/")
    assert f"lessons%2F{world.lessons[1].pk}" in next_lesson["url"]
    assert Attempt.objects.get().passed is True
    assert access.can_open_lesson(world.student, world.lessons[1])
    assert state() == {}


def test_failed_quiz_hides_answers_and_offers_retry(tg: FakeTelegram, world: World) -> None:
    connect(world.student)

    play(tg, world, wrong={"SINGLE", "MULTIPLE", "TEXT", "ORDER", "MATCH"})

    result = tg.last
    assert "Natija: 0% (0/5)" in result["text"] and "70% kerak" in result["text"]
    retry, video = buttons(result)
    assert retry["callback_data"] == f"qn:{world.quiz.pk}"
    assert video["text"] == "🎬 Videoni ko'rish"
    # To'g'ri javoblar va izohlar test o'tilmaguncha ko'rsatilmaydi.
    everything = " ".join([*tg.texts, *(edit["text"] for edit in tg.edits)])
    assert "To'g'ri javob" not in everything and "belgilash tili" not in everything

    handle_update(press(f"qn:{world.quiz.pk}"))
    assert Attempt.objects.count() == 2
    assert "5 ta savol" in tg.messages[-2]["text"]


def test_passed_quiz_reviews_mistakes_with_explanation(tg: FakeTelegram, world: World) -> None:
    connect(world.student)

    play(tg, world, wrong={"SINGLE"})

    review = tg.last["text"]
    assert "80% (4/5) ⭐⭐" in review
    assert "Xatolar ustida ishlash" in review
    assert "Siz: High Tech Modern Language" in review
    assert "To'g'ri javob: HyperText Markup Language" in review
    assert "💡 HTML — sahifa tuzilmasi uchun belgilash tili." in review


def test_selection_is_kept_and_stale_buttons_are_refused(tg: FakeTelegram, world: World) -> None:
    connect(world.student)
    handle_update(press(f"qs:{world.quiz.pk}"))
    ref, layout = current()
    handle_update(press(f"qa:{ref}:{spot(layout, 'HyperText Markup Language')}"))

    # Eski savol tugmasi.
    handle_update(press(f"qa:{ref}:1"))
    assert "yopilgan" in tg.notices[-1]
    # Bir nechta javobli savolda bo'sh "Tayyor".
    multiple, layout = current()
    handle_update(press(f"qd:{multiple}"))
    assert "Kamida bitta" in tg.notices[-1]
    handle_update(press(f"qt:{multiple}:{spot(layout, '<div>')}"))
    assert state()["sel"] == [spot(layout, "<div>")]
    assert "✅ " in str(tg.edits[-1]["reply_markup"])


def test_menu_button_is_not_taken_as_text_answer(tg: FakeTelegram, world: World) -> None:
    connect(world.student)
    handle_update(press(f"qs:{world.quiz.pk}"))
    answer()
    answer()
    assert BotChat.objects.get(chat_id=TG_ID).state["await"] == "text"

    handle_update(message("📚 Kurslarim"))

    assert "Kurslaringiz" in tg.last["text"]
    assert Question.objects.get(pk=state()["q"]).kind == Question.Kind.TEXT
    answer()
    assert tg.edits[-1]["text"].endswith("✅ To'g'ri")


def test_unfinished_quiz_is_resumed(tg: FakeTelegram, world: World) -> None:
    connect(world.student)
    handle_update(press(f"qs:{world.quiz.pk}"))
    answer()

    handle_update(message("📝 Testlar"))
    [start] = buttons(tg.last)
    assert start["callback_data"] == f"qs:{world.quiz.pk}" and start["text"].startswith("▶️")
    handle_update(press(start["callback_data"]))

    assert "Testni davom ettiramiz" in tg.messages[-2]["text"]
    assert "2/5." in tg.last["text"]
    assert Attempt.objects.count() == 1


def test_next_lesson_quiz_waits_for_previous_one(tg: FakeTelegram, world: World) -> None:
    connect(world.student)
    second = Quiz.objects.create(lesson=world.lessons[1], title="CSS")
    import_questions(second, parse("? CSS nima?\n+ Uslublar\n- Dastur\n"))

    handle_update(message("📝 Testlar"))
    assert [item["callback_data"] for item in buttons(tg.last)] == [f"qs:{world.quiz.pk}"]
    handle_update(press(f"qs:{second.pk}"))
    assert "avval «Dars 1» darsining testidan o'ting" in tg.last["text"]

    play(tg, world)
    handle_update(message("📝 Testlar"))
    assert [item["callback_data"] for item in buttons(tg.last)] == [f"qs:{second.pk}"]
    assert "O'tilgan testlar: 1" in tg.last["text"]


def test_offline_quiz_opens_after_teacher_covers_lesson(
    tg: FakeTelegram, world: World, django_capture_on_commit_callbacks: Any
) -> None:
    connect(world.student)
    world.group.study_format = "OFFLINE"
    world.group.save()

    handle_update(press(f"qs:{world.quiz.pk}"))
    assert "ustoz darsni o'tgach ochiladi" in tg.last["text"]

    record = GroupLesson.objects.create(group=world.group, lesson=world.lessons[0])
    tg.clear()
    with django_capture_on_commit_callbacks(execute=True):
        live.announce(record)

    notification = Notification.objects.get(user=world.student)
    assert notification.quiz_id == world.quiz.pk
    [sent] = tg.messages
    assert {"text": "📝 Testni boshlash", "callback_data": f"qs:{world.quiz.pk}"} in buttons(sent)
    handle_update(press(f"qs:{world.quiz.pk}"))
    assert "1/5." in tg.last["text"]
