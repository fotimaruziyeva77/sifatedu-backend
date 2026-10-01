"""Darsga kirish huquqi: eng muhim tekshiruv — sotib olmagan video URL orqali ochilmaydi."""

from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.catalog.models import Category, Course, Lesson, Module
from apps.learning.models import Enrollment, LessonProgress
from apps.users.models import User
from apps.videos.models import VideoAsset

pytestmark = pytest.mark.django_db

READY_VARIANTS = [
    {"height": 360, "width": 640, "bandwidth": 985_600, "playlist": "360p/index.m3u8"}
]


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def course(db: Any) -> Course:
    category = Category.objects.create(slug="dasturlash", name_uz="Dasturlash")
    return Course.objects.create(
        slug="frontend",
        title_uz="Frontend",
        category=category,
        status=Course.Status.PUBLISHED,
        price_online=1_800_000,
    )


@pytest.fixture
def lessons(course: Course) -> tuple[Lesson, Lesson]:
    module = Module.objects.create(course=course, title_uz="Modul")
    video = VideoAsset.objects.create(
        title="Dars videosi",
        status=VideoAsset.Status.READY,
        duration_sec=600,
        variants=READY_VARIANTS,
    )
    free = Lesson.objects.create(
        module=module, title_uz="Bepul dars", is_preview=True, order=0, video=video
    )
    paid = Lesson.objects.create(
        module=module, title_uz="Pullik dars", is_preview=False, order=1, video=video
    )
    return free, paid


@pytest.fixture
def student(db: Any) -> User:
    return User.objects.create_user(phone="+998901112233", password="Parol12345")


def urls(lesson: Lesson) -> list[str]:
    """Videoni ochishga imkon beradigan barcha manzillar."""
    return [
        f"/api/v1/lessons/{lesson.pk}/",
        f"/api/v1/lessons/{lesson.pk}/hls/master.m3u8",
        f"/api/v1/lessons/{lesson.pk}/hls/360p.m3u8",
        f"/api/v1/lessons/{lesson.pk}/hls/key",
    ]


def test_preview_lesson_is_open_to_everyone(client: APIClient, lessons: Any) -> None:
    free, _paid = lessons

    response = client.get(f"/api/v1/lessons/{free.pk}/")

    assert response.status_code == 200
    assert response.json()["is_preview"] is True


def test_anonymous_cannot_open_paid_lesson(client: APIClient, lessons: Any) -> None:
    _free, paid = lessons

    for url in urls(paid):
        assert client.get(url).status_code == 403, url


def test_logged_in_without_payment_cannot_open_paid_lesson(
    client: APIClient, lessons: Any, student: User
) -> None:
    _free, paid = lessons
    client.force_authenticate(student)

    for url in urls(paid):
        response = client.get(url)
        assert response.status_code == 403, url
        assert response.json()["error"]["code"] == "permission_denied"


def test_enrolled_student_opens_paid_lesson(
    client: APIClient, course: Course, lessons: Any, student: User
) -> None:
    _free, paid = lessons
    Enrollment.objects.create(user=student, course=course, source=Enrollment.Source.PAYMENT)
    client.force_authenticate(student)

    response = client.get(f"/api/v1/lessons/{paid.pk}/")

    assert response.status_code == 200
    assert response.json()["video"]["hls_url"].endswith("/hls/master.m3u8")


def test_expired_offline_enrollment_closes_access(
    client: APIClient, course: Course, lessons: Any, student: User
) -> None:
    """Offlayn oylik to'lov tugagach kirish yopiladi."""
    _free, paid = lessons
    Enrollment.objects.create(
        user=student,
        course=course,
        study_format=Enrollment.Format.OFFLINE,
        expires_at=timezone.now() - timedelta(days=1),
    )
    client.force_authenticate(student)

    assert client.get(f"/api/v1/lessons/{paid.pk}/").status_code == 403


def test_cancelled_enrollment_closes_access(
    client: APIClient, course: Course, lessons: Any, student: User
) -> None:
    _free, paid = lessons
    Enrollment.objects.create(user=student, course=course, status=Enrollment.Status.CANCELLED)
    client.force_authenticate(student)

    assert client.get(f"/api/v1/lessons/{paid.pk}/").status_code == 403


def test_free_course_is_open_to_logged_in_students(
    client: APIClient, course: Course, lessons: Any, student: User
) -> None:
    _free, paid = lessons
    Course.objects.filter(pk=course.pk).update(is_free=True)
    client.force_authenticate(student)

    assert client.get(f"/api/v1/lessons/{paid.pk}/").status_code == 200
    # Anonim foydalanuvchi bepul kursni ham ko'rmaydi: avval ro'yxatdan o'tadi.
    client.force_authenticate(None)
    assert client.get(f"/api/v1/lessons/{paid.pk}/").status_code == 403


def test_staff_opens_everything(client: APIClient, lessons: Any, db: Any) -> None:
    _free, paid = lessons
    staff = User.objects.create_user(phone="+998909998877", password="Parol12345", is_staff=True)
    client.force_authenticate(staff)

    assert client.get(f"/api/v1/lessons/{paid.pk}/").status_code == 200


def test_key_is_binary_and_not_cached(
    client: APIClient, course: Course, lessons: Any, student: User
) -> None:
    _free, paid = lessons
    Enrollment.objects.create(user=student, course=course)
    client.force_authenticate(student)

    response = client.get(f"/api/v1/lessons/{paid.pk}/hls/key")

    assert response.status_code == 200
    assert len(response.content) == 16  # AES-128
    assert response["Cache-Control"] == "no-store"


def test_video_not_ready_returns_404(
    client: APIClient, course: Course, lessons: Any, student: User
) -> None:
    _free, paid = lessons
    VideoAsset.objects.filter(pk=paid.video_id).update(status=VideoAsset.Status.PROCESSING)
    Enrollment.objects.create(user=student, course=course)
    client.force_authenticate(student)

    assert client.get(f"/api/v1/lessons/{paid.pk}/hls/master.m3u8").status_code == 404
    # Dars sahifasi ochiladi, lekin videosi yo'q deb ko'rsatadi.
    payload = client.get(f"/api/v1/lessons/{paid.pk}/").json()
    assert payload["video"]["status"] == VideoAsset.Status.PROCESSING
    assert payload["video"]["hls_url"] == ""


def test_lesson_has_prev_next(
    client: APIClient, course: Course, lessons: Any, student: User
) -> None:
    free, paid = lessons
    Enrollment.objects.create(user=student, course=course)
    client.force_authenticate(student)

    first = client.get(f"/api/v1/lessons/{free.pk}/").json()
    second = client.get(f"/api/v1/lessons/{paid.pk}/").json()

    assert (first["prev_id"], first["next_id"]) == (None, paid.pk)
    assert (second["prev_id"], second["next_id"]) == (free.pk, None)


def test_watermark_shows_account(
    client: APIClient, course: Course, lessons: Any, student: User
) -> None:
    _free, paid = lessons
    Enrollment.objects.create(user=student, course=course)
    client.force_authenticate(student)

    watermark = client.get(f"/api/v1/lessons/{paid.pk}/").json()["watermark"]

    assert watermark == f"2233 · #{student.pk}"


class TestProgress:
    def test_saves_position(
        self, client: APIClient, course: Course, lessons: Any, student: User
    ) -> None:
        _free, paid = lessons
        Enrollment.objects.create(user=student, course=course)
        client.force_authenticate(student)

        response = client.put(
            f"/api/v1/lessons/{paid.pk}/progress/", {"position_sec": 120}, format="json"
        )

        assert response.status_code == 200
        assert response.json() == {"position_sec": 120, "watched_sec": 120, "completed": False}

    def test_ninety_percent_completes_lesson(
        self, client: APIClient, course: Course, lessons: Any, student: User
    ) -> None:
        _free, paid = lessons
        Enrollment.objects.create(user=student, course=course)
        client.force_authenticate(student)

        # Video 600 soniya: 540 = 90%.
        assert not client.put(
            f"/api/v1/lessons/{paid.pk}/progress/", {"position_sec": 539}, format="json"
        ).json()["completed"]
        assert client.put(
            f"/api/v1/lessons/{paid.pk}/progress/", {"position_sec": 540}, format="json"
        ).json()["completed"]

    def test_rewinding_keeps_completion_and_watched_time(
        self, client: APIClient, course: Course, lessons: Any, student: User
    ) -> None:
        _free, paid = lessons
        Enrollment.objects.create(user=student, course=course)
        client.force_authenticate(student)
        client.put(f"/api/v1/lessons/{paid.pk}/progress/", {"position_sec": 600}, format="json")

        again = client.put(
            f"/api/v1/lessons/{paid.pk}/progress/", {"position_sec": 10}, format="json"
        ).json()

        assert again["position_sec"] == 10
        assert again["watched_sec"] == 600
        assert again["completed"] is True

    def test_position_cannot_exceed_duration(
        self, client: APIClient, course: Course, lessons: Any, student: User
    ) -> None:
        _free, paid = lessons
        Enrollment.objects.create(user=student, course=course)
        client.force_authenticate(student)

        response = client.put(
            f"/api/v1/lessons/{paid.pk}/progress/", {"position_sec": 5_000}, format="json"
        )

        assert response.json()["position_sec"] == 600

    def test_without_access_progress_is_rejected(
        self, client: APIClient, lessons: Any, student: User
    ) -> None:
        _free, paid = lessons
        client.force_authenticate(student)

        response = client.put(
            f"/api/v1/lessons/{paid.pk}/progress/", {"position_sec": 10}, format="json"
        )

        assert response.status_code == 403
        assert not LessonProgress.objects.exists()


class TestMaterials:
    def test_materials_come_with_lesson(
        self, client: APIClient, course: Course, lessons: Any, student: User
    ) -> None:
        from django.core.files.base import ContentFile

        from apps.catalog.models import LessonMaterial

        _free, paid = lessons
        LessonMaterial.objects.create(
            lesson=paid,
            kind=LessonMaterial.Kind.CODE,
            title="index.html",
            code="<h1>Salom</h1>",
            language="html",
            order=0,
        )
        LessonMaterial.objects.create(
            lesson=paid,
            kind=LessonMaterial.Kind.LINK,
            title="MDN",
            url="https://developer.mozilla.org",
            order=1,
        )
        slides = LessonMaterial(
            lesson=paid, kind=LessonMaterial.Kind.FILE, title="Slaydlar", order=2
        )
        slides.file.save("slaydlar.pdf", ContentFile(b"%PDF-1.4 sinov"), save=True)
        Enrollment.objects.create(user=student, course=course)
        client.force_authenticate(student)

        with patch("apps.videos.s3.sign_get", return_value="https://s3/signed") as sign:
            materials = client.get(f"/api/v1/lessons/{paid.pk}/").json()["materials"]

        assert [item["kind"] for item in materials] == ["CODE", "LINK", "FILE"]
        assert materials[0]["code"] == "<h1>Salom</h1>"
        assert materials[1]["url"] == "https://developer.mozilla.org"
        # Fayl — faqat qisqa muddatli imzolangan havola bilan, asl nomi bilan yuklanadi.
        assert materials[2]["url"] == "https://s3/signed"
        assert sign.call_args.kwargs["download_name"] == "slaydlar.pdf"
        assert materials[2]["size"] == len(b"%PDF-1.4 sinov")

    def test_materials_are_hidden_without_access(
        self, client: APIClient, lessons: Any, student: User
    ) -> None:
        from apps.catalog.models import LessonMaterial

        _free, paid = lessons
        LessonMaterial.objects.create(
            lesson=paid, kind=LessonMaterial.Kind.CODE, title="yashirin", code="sir"
        )
        client.force_authenticate(student)

        response = client.get(f"/api/v1/lessons/{paid.pk}/")

        assert response.status_code == 403
        assert "sir" not in response.content.decode()
