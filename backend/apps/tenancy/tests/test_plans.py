"""Tarif: yopiq bo'lim hamma joyda yopiq, chegarada yangisi qo'shilmaydi, muddat o'tsa to'xtaydi."""

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bot import menu, router
from apps.bot.models import BotChat
from apps.catalog.models import Category, Course, Lesson, Module
from apps.content.services import get_site_payload
from apps.integrations.testing import set_keys
from apps.learning import access, roster
from apps.learning.models import Enrollment, StudyGroup
from apps.notifications import services as notifications
from apps.notifications import telegram
from apps.notifications.models import Delivery, Notification
from apps.rewards import referral
from apps.rewards import services as rewards
from apps.rewards.models import Coupon, Entry
from apps.tenancy import tasks
from apps.tenancy.db import connection
from apps.tenancy.limits import LimitReached, check_disk
from apps.tenancy.models import Center, Plan
from apps.tenancy.sections import Feature
from apps.tenancy.storage import CenterS3Storage
from apps.users.models import SocialAccount, User
from apps.users.roles import Role, set_roles
from config.celery import app

pytestmark = pytest.mark.django_db

TEST_HOST = "testserver"
PLATFORM_HOST = "platform.testserver"


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def student() -> User:
    return User.objects.create_user(phone="+998901000001", first_name="Ali")


def use_plan(*features: str, **values: Any) -> Plan:
    plan = Plan.objects.create(name="Sinov tarifi", features=list(features), **values)
    Center.objects.filter(schema_name=connection.schema_name).update(plan=plan)
    return plan


def center() -> Center:
    return Center.objects.get(schema_name=connection.schema_name)


def code(response: Any) -> str:
    return str(response.json()["error"]["code"])


# --- Bo'limlar ---


def test_no_plan_opens_everything() -> None:
    assert center().features == frozenset(Feature.values)


def test_plan_and_extra_features_are_combined() -> None:
    use_plan(Feature.BOT)
    Center.objects.filter(schema_name=connection.schema_name).update(extra_features=[Feature.VIDEO])

    assert center().features == {Feature.BOT, Feature.VIDEO}


@pytest.mark.parametrize("section", [Feature.EXAMS, Feature.PLACEMENT, Feature.AI])
def test_section_using_question_bank_opens_lessons(section: str) -> None:
    use_plan(section)

    assert Feature.LESSONS in center().features


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/homework/"),
        ("post", "/api/v1/quizzes/1/attempts/"),
        ("get", "/api/v1/exams/"),
        ("get", "/api/v1/daily-test/"),
        ("get", "/api/v1/certificates/"),
        ("get", "/api/v1/rewards/"),
        ("get", "/api/v1/shop/"),
        ("post", "/api/v1/assistant/chat/"),
        ("get", "/api/v1/teacher/quiz-drafts/1/"),
        ("get", "/api/v1/lessons/1/hls/key"),
        ("get", "/api/v1/admin/videos/1/"),
        ("post", "/api/v1/bot/quizzes/1/link/"),
        ("post", "/api/v1/orders/"),
    ],
)
def test_closed_section_answers_403(
    client: APIClient, student: User, method: str, path: str
) -> None:
    use_plan()
    client.force_authenticate(student)

    response = getattr(client, method)(path)

    assert response.status_code == 403
    assert code(response) == "feature_disabled"


@pytest.mark.parametrize(
    ("path", "status"),
    [
        ("/api/v1/orders/", 200),
        ("/api/v1/rewards/discount/", 200),
        ("/api/v1/certificates/SE-0000-NOPE00/", 404),
        ("/api/v1/notifications/", 200),
        ("/api/v1/my/courses/", 200),
    ],
)
def test_core_and_issued_things_stay_open(
    client: APIClient, student: User, path: str, status: int
) -> None:
    use_plan()
    client.force_authenticate(student)

    assert client.get(path).status_code == status


def test_payment_callback_stays_open(client: APIClient) -> None:
    use_plan()

    response = client.post("/api/v1/payments/click/prepare/", {})

    assert response.status_code != 403


def test_open_section_is_not_touched(client: APIClient, student: User) -> None:
    use_plan(Feature.LESSONS)
    client.force_authenticate(student)

    assert client.get("/api/v1/homework/").status_code == 200


def test_center_info_lists_features(client: APIClient) -> None:
    use_plan(Feature.BOT)

    data = client.get("/api/v1/center/").json()

    assert (data["state"], data["features"]) == ("active", ["bot"])


def test_site_payload_follows_plan_despite_cache(settings: Any) -> None:
    settings.ASSISTANT_DRY_RUN = True
    set_keys(click_service_id="1")
    set_keys(click_secret_key="x")
    assert get_site_payload()["settings"]["payments_enabled"] is True

    use_plan()

    site = get_site_payload()["settings"]
    assert site["payments_enabled"] is False
    assert site["assistant_enabled"] is False


# --- Admin panel ---


def test_closed_section_is_closed_for_superuser() -> None:
    admin = User.objects.create_superuser(phone="+998901000002")
    use_plan(Feature.LESSONS)

    assert admin.has_perm("quizzes.view_quiz")
    assert not admin.has_perm("rewards.view_entry")
    assert not admin.has_module_perms("shop")
    assert admin.has_perm("leads.view_lead")


def test_model_of_other_section_follows_its_own_section() -> None:
    admin = User.objects.create_superuser(phone="+998901000003")
    use_plan(Feature.PLACEMENT)

    assert admin.has_perm("rewards.view_coupon")
    assert admin.has_module_perms("rewards")
    assert not admin.has_perm("rewards.view_entry")
    assert admin.has_perm("catalog.view_lessonslides")
    assert not admin.has_perm("quizzes.view_quizdraft")


def test_admin_page_of_closed_section_is_forbidden(client: APIClient) -> None:
    client.force_login(User.objects.create_superuser(phone="+998901000004"))
    use_plan()

    assert client.get("/admin/rewards/entry/").status_code == 403
    assert client.get("/admin/leads/lead/").status_code == 200


# --- Muddat ---


def expire(days_ago: int, *, grace_days: int = 7) -> None:
    plan = Plan.objects.create(
        name="Muddatli", features=list(Feature.values), grace_days=grace_days
    )
    Center.objects.filter(schema_name=connection.schema_name).update(
        plan=plan, paid_until=timezone.localdate() - timedelta(days=days_ago)
    )


def test_state_passes_through_grace_to_blocked() -> None:
    expire(0)
    assert center().state == Center.State.ACTIVE
    Center.objects.filter(schema_name=connection.schema_name).update(
        paid_until=timezone.localdate() - timedelta(days=3)
    )
    assert center().state == Center.State.GRACE
    Center.objects.filter(schema_name=connection.schema_name).update(
        paid_until=timezone.localdate() - timedelta(days=8)
    )
    assert center().state == Center.State.BLOCKED


def test_grace_keeps_everything_working(client: APIClient, student: User) -> None:
    expire(3)
    client.force_authenticate(student)

    assert client.get("/api/v1/notifications/").status_code == 200


def test_blocked_center_stops_but_says_why(client: APIClient, student: User) -> None:
    expire(30)
    client.force_authenticate(student)

    response = client.get("/api/v1/notifications/")

    assert response.status_code == 402
    assert code(response) == "center_blocked"
    assert client.get("/api/v1/center/").json()["state"] == "blocked"
    assert client.get("/api/v1/health/").status_code == 200
    assert client.get("/admin/login/").status_code == 402


def test_suspended_center_is_blocked_without_a_date(client: APIClient) -> None:
    Center.objects.filter(schema_name=connection.schema_name).update(is_suspended=True)

    assert client.get("/api/v1/courses/").status_code == 402


def test_blocked_center_still_receives_payment_callback(client: APIClient) -> None:
    expire(30)

    assert client.post("/api/v1/payments/click/prepare/", {}).status_code != 402


def test_staff_sees_days_left(client: APIClient) -> None:
    staff = User.objects.create_user(phone="+998901000005", is_staff=True)
    Center.objects.filter(schema_name=connection.schema_name).update(
        paid_until=timezone.localdate() + timedelta(days=3)
    )
    client.force_authenticate(staff)

    assert client.get("/api/v1/me/").json()["subscription_days_left"] == 3


def test_student_does_not_see_days_left(client: APIClient, student: User) -> None:
    Center.objects.filter(schema_name=connection.schema_name).update(
        paid_until=timezone.localdate() + timedelta(days=3)
    )
    client.force_authenticate(student)

    assert client.get("/api/v1/me/").json()["subscription_days_left"] is None


# --- Fon vazifalar ---


@app.task(name="apps.rewards.tasks.tenancy_test_closed")
def rewards_task() -> str:
    return "bajarildi"


@app.task(name="apps.assistant.tasks.anonymize_old_conversations_test")
def plain_ai_task() -> str:
    return "bajarildi"


def test_task_of_closed_section_is_skipped() -> None:
    use_plan()

    assert rewards_task.apply().get() is None


def test_task_of_open_section_runs() -> None:
    use_plan(Feature.REWARDS)

    assert rewards_task.apply().get() == "bajarildi"


def test_task_stops_in_blocked_center() -> None:
    expire(30)

    assert rewards_task.apply().get() is None


def test_retention_runs_with_ai_closed() -> None:
    use_plan()
    task = app.tasks["apps.assistant.tasks.anonymize_old_conversations"]

    with patch("apps.assistant.tasks.Conversation") as conversations:
        task.apply().get()

    assert conversations.objects.mock_calls


# --- Bog'liq mantiq ---


@pytest.fixture
def lesson() -> Lesson:
    category = Category.objects.create(slug="it", name_uz="IT")
    course = Course.objects.create(
        slug="python", title_uz="Python", category=category, status=Course.Status.PUBLISHED
    )
    module = Module.objects.create(course=course, title_uz="Kirish")
    return Lesson.objects.create(module=module, title_uz="Birinchi", is_preview=True)


def test_quiz_gate_is_empty_without_lessons_section(student: User) -> None:
    use_plan()

    with patch("apps.quizzes.models.Quiz.objects") as quizzes:
        assert access.quiz_gate(student, 1) == {}

    quizzes.filter.assert_not_called()


def test_lesson_payload_hides_closed_sections(client: APIClient, lesson: Lesson) -> None:
    use_plan()

    data = client.get(f"/api/v1/lessons/{lesson.pk}/").json()

    assert data["quiz"] is None
    assert data["homework"] is None
    assert data["slides"] is None
    assert data["tasks_locked"] is False


def test_no_points_without_rewards_section(student: User) -> None:
    use_plan()

    assert rewards.credit(student.pk, Entry.Reason.LESSON, key="k", xp=5) is None
    assert not Entry.objects.exists()


def test_points_are_written_with_rewards_section(student: User) -> None:
    use_plan(Feature.REWARDS)

    assert rewards.credit(student.pk, Entry.Reason.LESSON, key="k", xp=5) is not None


def test_placement_coupon_survives_rewards_being_closed(student: User) -> None:
    use_plan(Feature.PLACEMENT)
    Coupon.objects.create(user=student, percent=20, kind=Coupon.Kind.PLACEMENT)
    Coupon.objects.create(user=student, percent=50, kind=Coupon.Kind.REFERRAL)

    discount = referral.discount_for(student)

    assert discount is not None
    assert discount.percent == 20


def test_no_coupon_when_both_sections_closed(student: User) -> None:
    use_plan()
    Coupon.objects.create(user=student, percent=20, kind=Coupon.Kind.PLACEMENT)

    assert referral.discount_for(student) is None


def test_no_telegram_or_sms_without_bot_section(student: User, settings: Any) -> None:
    set_keys(telegram_token="t")
    set_keys(telegram_username="sinov_bot")
    use_plan()
    account = SocialAccount.objects.create(
        user=student, provider=SocialAccount.Provider.TELEGRAM, uid="1", notify=True
    )

    built = notifications.build(
        student, Notification.Kind.REWARD, title="t", sms_text="salom", account=account
    )

    assert built.telegram == ""
    assert built.sms == ""
    assert telegram.bot_username() == ""


def test_delivery_is_queued_with_bot_section(student: User, settings: Any) -> None:
    set_keys(telegram_token="t")
    use_plan(Feature.BOT)
    account = SocialAccount.objects.create(
        user=student, provider=SocialAccount.Provider.TELEGRAM, uid="1", notify=True
    )

    built = notifications.build(student, Notification.Kind.REWARD, title="t", account=account)

    assert built.telegram == Delivery.QUEUED


# --- Bot ---


def keyboard_texts(markup: dict[str, Any]) -> list[str]:
    return [button["text"] for row in markup["keyboard"] for button in row]


def test_bot_menu_shows_only_open_sections() -> None:
    use_plan(Feature.BOT)

    texts = keyboard_texts(menu.main_keyboard("uz", registered=True))

    assert "📝 Testlar" not in texts
    assert "💬 Savol berish" not in texts
    assert "🎁 Do'stni taklif qilish" not in texts
    assert "📚 Kurslarim" in texts


def test_bot_menu_is_full_on_full_plan() -> None:
    texts = keyboard_texts(menu.main_keyboard("uz", registered=True))

    assert "📝 Testlar" in texts
    assert "💬 Savol berish" in texts


def test_bot_refuses_stale_button_of_closed_section() -> None:
    use_plan(Feature.BOT)
    chat = BotChat.objects.create(chat_id=1, language="uz")

    notice = router.handle_callback(chat, {"first_name": "A"}, "qs:1", {})

    assert notice == "Bu bo'lim hozircha yopiq."


def test_bot_refuses_stale_menu_text_of_closed_section(student: User) -> None:
    use_plan(Feature.BOT)
    chat = BotChat.objects.create(chat_id=2, language="uz")

    with patch.object(router, "send") as send:
        router.run_menu(chat, student, "tests")

    send.assert_called_once_with(2, "Bu bo'lim hozircha yopiq.")


def test_bot_points_to_menu_when_ai_is_closed() -> None:
    use_plan(Feature.BOT)
    chat = BotChat.objects.create(chat_id=3, language="uz")

    with (
        patch.object(router, "send") as send,
        patch.object(router, "subscribed", return_value=True),
        patch.object(router, "ask_ai") as ask_ai,
    ):
        router.handle_message(chat, {"id": 3}, {"text": "salom"})

    ask_ai.assert_not_called()
    send.assert_called_once_with(3, "Kerakli bo'limni menyudan tanlang.")


# --- Cheklovlar ---


@pytest.fixture
def teacher() -> User:
    return User.objects.create_user(phone="+998901000099", first_name="Ustoz")


@pytest.fixture
def group(lesson: Lesson, teacher: User) -> StudyGroup:
    return StudyGroup.objects.create(name="A", course=lesson.module.course, teacher=teacher)


def add_to_group(group: StudyGroup, phone: str) -> None:
    roster.add_student(group, phone=phone, first_name="Vali")


def test_student_limit_stops_new_student(group: StudyGroup) -> None:
    use_plan(max_students=1)
    add_to_group(group, "+998901000011")

    with pytest.raises(LimitReached):
        add_to_group(group, "+998901000012")

    assert Enrollment.objects.count() == 1
    assert not User.objects.filter(phone="+998901000012").exists()


def test_existing_student_can_join_another_course(group: StudyGroup) -> None:
    use_plan(max_students=1)
    add_to_group(group, "+998901000011")
    category = Category.objects.get(slug="it")
    other = Course.objects.create(slug="js", title_uz="JS", category=category)
    second = StudyGroup.objects.create(name="B", course=other, teacher=group.teacher)

    add_to_group(second, "+998901000011")

    assert Enrollment.objects.count() == 2


def test_order_is_refused_at_student_limit(
    client: APIClient, student: User, group: StudyGroup
) -> None:
    use_plan(Feature.CLICK, max_students=1)
    set_keys(click_service_id="1", click_secret_key="x")
    add_to_group(group, "+998901000011")
    client.force_authenticate(student)
    Course.objects.filter(pk=group.course_id).update(price_online=100_000, study_format="ONLINE")

    response = client.post(
        "/api/v1/orders/", {"course": "python", "study_format": "ONLINE", "months": 1}
    )

    assert response.status_code == 403
    assert code(response) == "limit_reached"


def test_staff_limit_stops_new_staff() -> None:
    use_plan(max_staff=1)
    first = User.objects.create_user(phone="+998901000021")
    second = User.objects.create_user(phone="+998901000022")
    set_roles(first, [Role.TEACHER])

    with pytest.raises(LimitReached):
        set_roles(second, [Role.MANAGER])

    set_roles(first, [Role.TEACHER, Role.MANAGER])


def test_student_role_is_not_limited_as_staff() -> None:
    use_plan(max_staff=0)
    user = User.objects.create_user(phone="+998901000023")

    set_roles(user, [Role.STUDENT])


def fill_disk() -> None:
    use_plan(max_disk_gb=1)
    Center.objects.filter(schema_name=connection.schema_name).update(disk_bytes=2 * 1024**3)


def test_disk_limit_stops_new_upload() -> None:
    fill_disk()

    with pytest.raises(LimitReached):
        check_disk()


def test_disk_limit_stops_storage_save_in_request() -> None:
    fill_disk()
    storage = CenterS3Storage(bucket_name="b")

    with pytest.raises(LimitReached):
        storage._save("a.txt", ContentFile(b"x"))


def test_disk_limit_does_not_break_background_work() -> None:
    fill_disk()
    storage = CenterS3Storage(bucket_name="b")

    with (
        patch("apps.tenancy.storage.current_task", MagicMock()),
        patch("storages.backends.s3.S3Storage._save", return_value="a.txt") as saved,
    ):
        storage._save("a.txt", ContentFile(b"x"))

    saved.assert_called_once()


def test_refresh_usage_stores_numbers(student: User, group: StudyGroup) -> None:
    add_to_group(group, "+998901000011")
    User.objects.create_user(phone="+998901000031", is_staff=True)
    client = MagicMock()
    client.get_paginator.return_value.paginate.return_value = [
        {"Contents": [{"Key": "centers/test_center/a", "Size": 10}]}
    ]

    with patch.object(tasks.s3, "internal", return_value=client):
        tasks.refresh_usage()

    fresh = center()
    assert (fresh.students_count, fresh.staff_count, fresh.disk_bytes) == (1, 1, 20)


def test_first_center_does_not_count_other_centers_files(settings: Any) -> None:
    settings.LEGACY_STORAGE_SCHEMAS = [connection.schema_name]
    client = MagicMock()
    client.get_paginator.return_value.paginate.return_value = [
        {"Contents": [{"Key": "videos/a", "Size": 10}, {"Key": "centers/x/b", "Size": 99}]}
    ]

    with patch.object(tasks.s3, "internal", return_value=client):
        assert tasks.disk_usage() == 20


# --- Platforma paneli ---


@pytest.fixture
def platform_client(client: APIClient) -> APIClient:
    from django_tenants.utils import schema_context

    with schema_context("public"):
        client.force_login(User.objects.create_superuser(phone="+998901000041"))
    return client


def test_panel_lists_plans(platform_client: APIClient) -> None:
    response = platform_client.get("/admin/tenancy/plan/", HTTP_HOST=PLATFORM_HOST)

    assert response.status_code == 200
    assert "Standart" in response.content.decode()


def test_panel_plan_change_closes_section_at_once(
    platform_client: APIClient, client: APIClient, student: User
) -> None:
    first = connection.schema_name
    target = Center.objects.get(schema_name=first)
    start = Plan.objects.get(name="Start")

    response = platform_client.post(
        f"/admin/tenancy/center/{target.pk}/change/",
        {
            "name": target.name,
            "plan": start.pk,
            "domains-TOTAL_FORMS": 0,
            "domains-INITIAL_FORMS": 0,
            "domains-MIN_NUM_FORMS": 0,
            "domains-MAX_NUM_FORMS": 1000,
        },
        format="multipart",
        HTTP_HOST=PLATFORM_HOST,
    )

    assert response.status_code == 302
    assert Center.objects.get(pk=target.pk).plan == start
    assert client.get("/api/v1/rewards/", HTTP_HOST=TEST_HOST).status_code == 403
