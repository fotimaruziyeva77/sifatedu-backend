"""O'quvchi profili (22d): «Familiya Ism Otasining ismi», tug'ilgan sana, rasm (kvadrat JPEG)."""

import io
from datetime import date

import pytest
from PIL import Image
from rest_framework.test import APIClient

from apps.users import photos, profile
from apps.users.models import User

TODAY = date(2026, 10, 14)


def picture(size: tuple[int, int] = (900, 1200), image_format: str = "JPEG") -> bytes:
    buffer = io.BytesIO()
    mode = "RGBA" if image_format == "PNG" else "RGB"
    Image.new(mode, size, "#e31e24").save(buffer, format=image_format)
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Valiyev Aziz Akmal o'g'li", ("Valiyev", "Aziz", "Akmal o'g'li")),
        ("VALIYEV AZIZ AKMAL O‘G‘LI", ("Valiyev", "Aziz", "Akmal o'g'li")),
        ("  ergasheva   madina  ", ("Ergasheva", "Madina", "")),
        ("G'ulomova Gulnoza Baxtiyor qizi", ("G'ulomova", "Gulnoza", "Baxtiyor qizi")),
        ("Иванов Иван Иванович", ("Иванов", "Иван", "Иванович")),
        ("McLaren Anna-Maria", ("McLaren", "Anna-Maria", "")),
    ],
)
def test_full_name_is_read_in_passport_order(text: str, expected: tuple[str, str, str]) -> None:
    name = profile.parse_name(text)

    assert name is not None and (name.last, name.first, name.middle) == expected


@pytest.mark.parametrize(
    "text",
    ["Aziz", "❤️ALHAMDULILLAH❤️👍", "Aziz 2008", "A B", "Bir ikki uch tort besh olti", "Ali_v Vali"],
)
def test_nicknames_and_junk_are_not_names(text: str) -> None:
    assert profile.parse_name(text) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("14.03.2008", date(2008, 3, 14)),
        ("1/9/2015", date(2015, 9, 1)),
        ("14-03-2008", date(2008, 3, 14)),
        ("2008-03-14", date(2008, 3, 14)),
        (" 14 03 2008 ", date(2008, 3, 14)),
    ],
)
def test_birth_date_formats(text: str, expected: date) -> None:
    assert profile.parse_birth(text, TODAY) == expected


@pytest.mark.parametrize(
    "text", ["31.02.2008", "14.03.08", "14.03.2025", "01.01.1930", "bugun", "2008"]
)
def test_impossible_birth_dates_are_refused(text: str) -> None:
    assert profile.parse_birth(text, TODAY) is None


def test_photo_becomes_a_square_jpeg_and_junk_is_refused() -> None:
    for source in (picture((900, 1200)), picture((300, 200), "PNG")):
        content = photos.square_jpeg(source)
        with Image.open(io.BytesIO(content.read())) as image:
            assert (image.size, image.format) == ((512, 512), "JPEG")

    with pytest.raises(photos.PhotoError):
        photos.square_jpeg(b"not an image")
    with pytest.raises(photos.PhotoError):
        photos.square_jpeg(b"0" * (photos.MAX_BYTES + 1))


@pytest.mark.django_db
def test_staff_edit_confirms_the_name_and_replaces_the_photo() -> None:
    user = User.objects.create_user(phone="+998901000001", first_name="❤️ALHAMDULILLAH❤️")
    assert profile.missing(user) == [profile.NAME, profile.BIRTH, profile.PHOTO]

    profile.update_by_staff(
        user,
        {
            "first_name": "Aziz",
            "last_name": "Valiyev",
            "middle_name": "Akmal o'g'li",
            "birth_date": date(2008, 3, 14),
            "photo": picture(),
        },
    )

    user.refresh_from_db()
    assert user.get_full_name() == "Aziz Valiyev" and profile.complete(user)
    assert profile.missing(user) == []
    first = user.avatar.name
    profile.update_by_staff(user, {"photo": picture((640, 480))})
    assert user.avatar.name != first and not user.avatar.storage.exists(first)
    profile.update_by_staff(user, {"remove_photo": True})
    user.refresh_from_db()
    assert not user.avatar and profile.missing(user) == [profile.PHOTO]


@pytest.mark.django_db
def test_student_fills_middle_name_and_birth_date_on_the_site() -> None:
    user = User.objects.create_user(phone="+998901000002", first_name="Aziz")
    client = APIClient()
    client.force_authenticate(user)

    wrong = client.patch("/api/v1/me/", {"birth_date": "2025-01-01"}, format="json")
    saved = client.patch(
        "/api/v1/me/",
        {"last_name": "Valiyev", "middle_name": "Akmal o'g'li", "birth_date": "2008-03-14"},
        format="json",
    )

    assert wrong.status_code == 400 and "birth_date" in str(wrong.json())
    assert saved.status_code == 200, saved.json()
    assert (saved.json()["middle_name"], saved.json()["birth_date"]) == (
        "Akmal o'g'li",
        "2008-03-14",
    )
    user.refresh_from_db()
    assert user.profile_confirmed_at is not None
