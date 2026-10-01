"""Video: kalit shifrlash, ffmpeg buyruqlari, playlist va yuklash oqimi."""

import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.users.models import User
from apps.users.roles import Role, set_roles
from apps.videos import crypto, ffmpeg, hls
from apps.videos.models import VideoAsset

pytestmark = pytest.mark.django_db


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def staff(db: Any) -> User:
    # Video yuklash huquqi rol orqali (o'qituvchi yoki admin): faqat `is_staff` yetmaydi.
    user = User.objects.create_user(phone="+998901112233", password="Parol12345")
    set_roles(user, [Role.TEACHER])
    user.refresh_from_db()
    return user


class TestCrypto:
    def test_key_round_trip(self) -> None:
        key = crypto.new_key()

        assert len(key) == crypto.AES_KEY_BYTES
        assert crypto.unseal(crypto.seal(key)) == key

    def test_sealed_key_is_not_plain_text(self) -> None:
        key = crypto.new_key()

        assert key not in crypto.seal(key).encode()

    def test_wrong_secret_cannot_open(self, settings: Any) -> None:
        token = crypto.seal(crypto.new_key())
        settings.VIDEO_KEY_SECRET = "boshqa-sir"

        with pytest.raises(ValueError):
            crypto.unseal(token)

    def test_key_is_created_once(self) -> None:
        video = VideoAsset.objects.create(title="Test")

        first = video.ensure_key()

        assert video.ensure_key() == first
        assert video.sealed_key


class TestRenditions:
    def test_does_not_upscale(self) -> None:
        assert [item.height for item in ffmpeg.renditions_for(720)] == [360, 480, 720]

    def test_small_source_still_gets_one_quality(self) -> None:
        assert [item.height for item in ffmpeg.renditions_for(240)] == [360]

    def test_480p_fits_under_one_and_half_mbit(self) -> None:
        """TZ: 480p 1.5 Mbit/s da uzilmasligi kerak."""
        rendition = next(item for item in ffmpeg.RENDITIONS if item.height == 480)

        assert (rendition.video_kbps + rendition.audio_kbps) * 1000 < 1_500_000

    def test_hls_command_encrypts_and_keeps_audio_optional(self) -> None:
        base = Path(tempfile.gettempdir())
        command = ffmpeg.hls_command(
            base / "src", base / "out", ffmpeg.RENDITIONS[0], base / "key.info"
        )

        assert "-hls_key_info_file" in command
        assert "0:a:0?" in command
        assert command[command.index("-hls_playlist_type") + 1] == "vod"


class TestPlaylists:
    @pytest.fixture
    def video(self, db: Any) -> VideoAsset:
        return VideoAsset.objects.create(
            title="Dars",
            status=VideoAsset.Status.READY,
            width=1280,
            height=720,
            variants=[
                {"height": 360, "width": 640, "bandwidth": 985_600, "playlist": "360p/index.m3u8"},
                {
                    "height": 720,
                    "width": 1280,
                    "bandwidth": 2_890_800,
                    "playlist": "720p/index.m3u8",
                },
            ],
        )

    def test_master_lists_qualities_low_to_high(self, video: VideoAsset) -> None:
        body = hls.master(video, "/api/v1/lessons/1/hls/{name}.m3u8")

        assert body.startswith("#EXTM3U")
        assert "/api/v1/lessons/1/hls/360p.m3u8" in body
        assert body.index("360p") < body.index("720p")
        assert "RESOLUTION=1280x720" in body

    def test_rendition_signs_segments_and_rewrites_key(self, video: VideoAsset) -> None:
        stored = (
            "#EXTM3U\n"
            '#EXT-X-KEY:METHOD=AES-128,URI="sifat://key",IV=0x00\n'
            "#EXTINF:6.0,\n"
            "seg_0000.ts\n"
            "#EXT-X-ENDLIST\n"
        )

        # boto3 imzosi katta harf bilan: shuning uchun argument nomlari shunday.
        def fake_get(Bucket: str, Key: str) -> dict[str, Any]:
            assert Key == f"{video.hls_prefix}/360p/index.m3u8"
            return {"Body": _Body(stored.encode())}

        with (
            patch("apps.videos.s3.internal") as internal,
            patch("apps.videos.s3.sign_get", side_effect=lambda key, ttl: f"https://s3/{key}?sig"),
        ):
            internal.return_value.get_object.side_effect = fake_get
            body = hls.rendition(video, "360p", "/api/v1/lessons/1/hls/key")

        assert body is not None
        assert 'URI="/api/v1/lessons/1/hls/key"' in body
        assert "IV=0x00" in body
        assert f"https://s3/{video.hls_prefix}/360p/seg_0000.ts?sig" in body

    def test_unknown_quality_returns_none(self, video: VideoAsset) -> None:
        assert hls.rendition(video, "1080p", "/key") is None


class TestUpload:
    def test_only_staff_can_start(self, client: APIClient, db: Any) -> None:
        student = User.objects.create_user(phone="+998907776655", password="Parol12345")
        client.force_authenticate(student)

        response = client.post(
            "/api/v1/admin/videos/", {"filename": "a.mp4", "size": 1000}, format="json"
        )

        assert response.status_code == 403

    def test_start_creates_multipart_session(
        self, client: APIClient, staff: User, settings: Any
    ) -> None:
        client.force_authenticate(staff)
        settings.VIDEO_PART_SIZE_MB = 16

        with patch("apps.videos.s3.start_multipart", return_value="upload-1") as start:
            response = client.post(
                "/api/v1/admin/videos/",
                {"filename": "dars.mp4", "size": 40 * 1024 * 1024, "content_type": "video/mp4"},
                format="json",
            )

        assert response.status_code == 201
        payload = response.json()
        assert payload["part_count"] == 3  # 40 MB / 16 MB
        assert payload["video"]["status"] == VideoAsset.Status.UPLOADING
        video = VideoAsset.objects.get(pk=payload["video"]["id"])
        assert video.upload_id == "upload-1"
        assert video.uploaded_by_id == staff.pk
        assert start.call_args.args[0] == video.source_key

    def test_too_large_file_is_rejected(
        self, client: APIClient, staff: User, settings: Any
    ) -> None:
        client.force_authenticate(staff)
        settings.MAX_VIDEO_SIZE_MB = 10

        response = client.post(
            "/api/v1/admin/videos/",
            {"filename": "katta.mp4", "size": 11 * 1024 * 1024},
            format="json",
        )

        assert response.status_code == 400
        assert not VideoAsset.objects.exists()

    def test_parts_are_signed(self, client: APIClient, staff: User) -> None:
        client.force_authenticate(staff)
        video = VideoAsset.objects.create(title="Dars", upload_id="upload-1")

        with patch("apps.videos.s3.sign_part", side_effect=lambda k, u, n, t: f"https://s3/{n}"):
            response = client.post(
                f"/api/v1/admin/videos/{video.pk}/parts/",
                {"part_numbers": [1, 2]},
                format="json",
            )

        assert response.json() == [
            {"part_number": 1, "url": "https://s3/1"},
            {"part_number": 2, "url": "https://s3/2"},
        ]

    def test_complete_queues_processing(self, client: APIClient, staff: User) -> None:
        client.force_authenticate(staff)
        video = VideoAsset.objects.create(title="Dars", upload_id="upload-1")

        with (
            patch("apps.videos.s3.finish_multipart", return_value=2048) as finish,
            patch("apps.videos.views.process_video.delay") as task,
        ):
            response = client.post(
                f"/api/v1/admin/videos/{video.pk}/complete/",
                {"parts": [{"part_number": 1, "etag": '"abc"'}]},
                format="json",
            )

        assert response.status_code == 200
        video.refresh_from_db()
        assert video.status == VideoAsset.Status.PROCESSING
        assert video.source_size == 2048
        assert video.upload_id == ""
        task.assert_called_once_with(video.pk)
        assert finish.call_args.args[2] == [{"part_number": 1, "etag": '"abc"'}]

    def test_complete_twice_is_rejected(self, client: APIClient, staff: User) -> None:
        client.force_authenticate(staff)
        video = VideoAsset.objects.create(title="Dars", status=VideoAsset.Status.PROCESSING)

        response = client.post(
            f"/api/v1/admin/videos/{video.pk}/complete/",
            {"parts": [{"part_number": 1, "etag": "abc"}]},
            format="json",
        )

        assert response.status_code == 400

    def test_abort_removes_unfinished_video(self, client: APIClient, staff: User) -> None:
        client.force_authenticate(staff)
        video = VideoAsset.objects.create(title="Dars", upload_id="upload-1")

        with patch("apps.videos.s3.cancel_multipart") as cancel:
            response = client.post(f"/api/v1/admin/videos/{video.pk}/abort/")

        assert response.status_code == 204
        assert not VideoAsset.objects.filter(pk=video.pk).exists()
        cancel.assert_called_once()


class _Body:
    """boto3 get_object javobidagi `Body` o'rniga."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data
