"""Daraja testi: natija va daraja, kupon (birinchi testga, bir marta), menejerga ariza, vaqti
tugagan testlar va kupon eslatmalari."""

from datetime import timedelta
from typing import Any

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.leads.models import Lead
from apps.learning.models import Enrollment
from apps.notifications.models import Notification
from apps.payments.models import Order
from apps.placement import services
from apps.placement.models import PlacementAttempt
from apps.quizzes.services import Layout, load_questions
from apps.quizzes.tests.conftest import right_answer, wrong_answer
from apps.rewards.models import Coupon, GameSettings
from apps.users.roles import Role, set_roles

from .conftest import World, make_user

pytestmark = pytest.mark.django_db


def respond(attempt: PlacementAttempt, right: int, *, upto: int = 99, now: Any = None) -> None:
    """Birinchi `right` ta savolga to'g'ri, qolganlariga noto'g'ri; `upto` tasigacha."""
    questions = load_questions(attempt.question_ids)
    for index, question_id in enumerate(attempt.question_ids[:upto]):
        payload = Layout.build(questions[question_id], attempt.seed).payload()
        response = right_answer(payload) if index < right else wrong_answer(payload)
        services.answer(attempt, question_id, response, now=now)


def test_good_result_gets_the_big_coupon_and_a_lead(
    world: World, django_capture_on_commit_callbacks: Any
) -> None:
    now = timezone.now()
    attempt = services.start(world.test, world.user, now=now)
    assert sorted(attempt.question_ids) == sorted(world.quiz.questions.values_list("pk", flat=True))
    assert attempt.deadline == now + timedelta(minutes=15)
    respond(attempt, right=5, now=now)

    with django_capture_on_commit_callbacks(execute=True):
        outcome = services.finish(attempt, now=now)

    assert (outcome.attempt.score, outcome.level) == (100, "good")
    coupon = outcome.coupon
    assert coupon is not None and coupon.kind == Coupon.Kind.PLACEMENT
    assert (coupon.percent, coupon.expires_at) == (25, now + timedelta(hours=72))
    lead = Lead.objects.get()
    assert (lead.source, lead.course, lead.phone) == ("BOT_TEST", world.course, world.user.phone)
    assert lead.name == "Aziz Valiyev" and lead.utm_source == "ig"
    assert lead.comment.startswith("Daraja testi (Python): 100%, kupon 25% (")
    assert lead.comment.endswith(" gacha), manba: ig")


def test_low_result_gets_the_small_coupon(world: World) -> None:
    attempt = services.start(world.test, world.user)
    respond(attempt, right=2)

    outcome = services.finish(attempt)

    assert (outcome.attempt.score, outcome.level) == (40, "middle")
    assert outcome.coupon is not None and outcome.coupon.percent == 15


def test_levels_follow_the_game_settings() -> None:
    assert [services.level_of(score) for score in (100, 70, 69, 40, 39, 0)] == [
        "good",
        "good",
        "middle",
        "middle",
        "beginner",
        "beginner",
    ]
    GameSettings.objects.filter(pk=GameSettings.load().pk).update(placement_good_percent=80)
    cache.clear()  # sozlamalar keshda
    assert services.level_of(75) == "middle"


def test_coupon_is_given_once(world: World, django_capture_on_commit_callbacks: Any) -> None:
    first = services.start(world.test, world.user)
    respond(first, right=1)
    with django_capture_on_commit_callbacks(execute=True):
        coupon = services.finish(first).coupon

    second = services.start(world.test, world.user)
    assert second.pk != first.pk
    respond(second, right=5)
    with django_capture_on_commit_callbacks(execute=True):
        outcome = services.finish(second)

    assert outcome.coupon is None and outcome.attempt.score == 100
    assert list(Coupon.objects.filter(user=world.user)) == [coupon]
    assert services.finish(first).coupon == coupon  # qayta yakunlash — o'sha natija
    lead = Lead.objects.get()  # 24 soat ichida bitta raqamdan — bitta ariza
    assert lead.submissions == 2 and "(Python): 100%" in lead.comment


def test_unanswered_questions_are_wrong_and_time_is_kept_on_the_server(world: World) -> None:
    now = timezone.now()
    attempt = services.start(world.test, world.user, now=now)
    respond(attempt, right=1, upto=1, now=now)
    late = attempt.deadline + timedelta(seconds=1)
    with pytest.raises(services.PlacementError, match="Vaqt tugadi"):
        services.answer(attempt, attempt.question_ids[1], {"choice": 1}, now=late)

    outcome = services.finish(attempt, now=late)

    assert (outcome.attempt.score, outcome.level) == (20, "beginner")
    assert outcome.attempt.finished_at == attempt.deadline
    assert services.seconds_left(attempt) == 0


def test_answers_are_checked(world: World) -> None:
    attempt = services.start(world.test, world.user)
    first, *_rest = attempt.question_ids
    with pytest.raises(services.PlacementError, match="formati"):
        services.answer(attempt, first, {"choice": 99})
    respond(attempt, right=1, upto=1)
    with pytest.raises(services.PlacementError, match="javob berilgan"):
        respond(attempt, right=1, upto=1)
    with pytest.raises(services.PlacementError, match="testda yo'q"):
        services.answer(attempt, 999_999, {"choice": 1})
    services.finish(attempt)
    with pytest.raises(services.PlacementError, match="yakunlangan"):
        services.answer(attempt, attempt.question_ids[1], {"choice": 1})


def test_running_attempt_is_resumed_and_an_expired_one_is_closed(world: World) -> None:
    now = timezone.now()
    first = services.start(world.test, world.user, now=now)
    assert services.start(world.test, world.user, now=now + timedelta(minutes=5)) == first

    second = services.start(world.test, world.user, now=now + timedelta(minutes=16))

    first.refresh_from_db()
    assert second != first and second.finished_at is None
    assert (first.score, first.finished_at) == (0, first.deadline)
    assert first.coupon is not None and first.coupon.percent == 15


def test_only_newcomers_take_the_test_and_get_coupons(world: World) -> None:
    student = make_user("+998901112233")
    Enrollment.objects.create(user=student, course=world.course)
    teacher = make_user("+998901112244")
    set_roles(teacher, [Role.TEACHER])
    teacher.refresh_from_db()
    former = make_user("+998901112255")
    Enrollment.objects.create(user=former, course=world.course, status=Enrollment.Status.CANCELLED)
    owner = make_user("+998901112266")
    owner.is_superuser = owner.is_staff = True
    owner.save(update_fields=["is_superuser", "is_staff"])

    assert [services.eligible(user) for user in (student, teacher, former, owner)] == [
        False,
        False,
        True,
        True,  # bosh admin — sinab ko'rish uchun
    ]
    with pytest.raises(services.PlacementError, match="yozilmaganlar uchun"):
        services.start(world.test, student)

    # Test paytida kursga yozilsa — natija bor, kupon yo'q.
    attempt = services.start(world.test, former)
    Enrollment.objects.filter(user=former).update(status=Enrollment.Status.ACTIVE)
    assert services.finish(attempt).coupon is None


def test_active_tests_need_questions(world: World) -> None:
    assert services.active_tests() == [world.test]
    world.quiz.questions.all().delete()
    assert services.active_tests() == []
    with pytest.raises(services.PlacementError, match="savol yo'q"):
        services.start(world.test, world.user)


def test_expired_attempts_are_closed_with_a_coupon_and_a_message(
    world: World, django_capture_on_commit_callbacks: Any
) -> None:
    now = timezone.now()
    attempt = services.start(world.test, world.user, now=now)
    respond(attempt, right=4, upto=4, now=now)

    assert services.close_expired(now=now + timedelta(minutes=14)) == 0
    with django_capture_on_commit_callbacks(execute=True):
        assert services.close_expired(now=now + timedelta(minutes=16)) == 1
    assert services.close_expired(now=now + timedelta(minutes=30)) == 0

    attempt.refresh_from_db()
    assert attempt.score == 80 and attempt.coupon is not None
    assert attempt.coupon.percent == 25
    notice = Notification.objects.get(user=world.user)
    assert notice.kind == Notification.Kind.COUPON and notice.link == "/dashboard/rewards"
    assert "natijangiz 80%" in notice.title and "25% chegirma" in notice.body
    assert Lead.objects.get().source == "BOT_TEST"


def coupon_for(world: World, hours_ago: float) -> Coupon:
    """Daraja testi kuponi: `hours_ago` soat oldin berilgan, 72 soat amal qiladi."""
    given = timezone.now() - timedelta(hours=hours_ago)
    coupon = services.issue_coupon(world.user, 80, now=given)
    Coupon.objects.filter(pk=coupon.pk).update(created_at=given)
    coupon.refresh_from_db()
    return coupon


def test_coupon_reminders_after_a_day_and_before_expiry(world: World) -> None:
    coupon = coupon_for(world, hours_ago=1)
    start = timezone.now()

    assert services.coupon_reminders(now=start) == 0
    assert services.coupon_reminders(now=start + timedelta(hours=24)) == 1
    assert services.coupon_reminders(now=start + timedelta(hours=25)) == 0
    assert services.coupon_reminders(now=start + timedelta(hours=60)) == 1
    assert services.coupon_reminders(now=start + timedelta(hours=61)) == 0
    assert services.coupon_reminders(now=start + timedelta(hours=72)) == 0  # muddati o'tdi

    first, last = Notification.objects.filter(user=world.user).order_by("pk")
    assert first.dedupe_key == f"coupon-first:{coupon.pk}" and "kutyapti" in first.title
    assert last.dedupe_key == f"coupon-last:{coupon.pk}" and "tugayapti" in last.title
    assert {first.kind, last.kind} == {Notification.Kind.COUPON}
    assert "25%" in last.title and "gacha amal qiladi" in last.body


def test_no_reminders_after_enrolment_or_use(world: World) -> None:
    coupon = coupon_for(world, hours_ago=30)
    order = Order.objects.create(user=world.user, course=world.course, amount=750_000)
    Coupon.objects.filter(pk=coupon.pk).update(order=order)
    assert services.coupon_reminders() == 1  # to'lov boshlangan, lekin tugamagan

    Notification.objects.all().delete()
    Coupon.objects.filter(pk=coupon.pk).update(used_at=timezone.now())
    assert services.coupon_reminders() == 0

    Coupon.objects.filter(pk=coupon.pk).update(used_at=None)
    Enrollment.objects.create(user=world.user, course=world.course)
    assert services.coupon_reminders() == 0
