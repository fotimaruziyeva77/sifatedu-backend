import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from apps.users.models import User
from apps.users.roles import Role


@pytest.mark.django_db
def test_create_user_hashes_password() -> None:
    user = User.objects.create_user(phone="+998901234567", password="Str0ng-pass")

    assert user.check_password("Str0ng-pass")
    assert user.password != "Str0ng-pass"
    assert not user.is_staff


@pytest.mark.django_db
def test_create_superuser_is_staff() -> None:
    user = User.objects.create_superuser(phone="+998901234568", password="Str0ng-pass")

    assert user.is_staff
    assert user.is_superuser


@pytest.mark.parametrize("phone", ["998901234567", "+99890123456", "+7901234567", "+998abcdefghi"])
def test_phone_format_is_validated(phone: str) -> None:
    user = User(phone=phone)

    with pytest.raises(ValidationError):
        user.full_clean(exclude=["password"])


@pytest.mark.django_db
def test_role_groups_exist() -> None:
    names = set(Group.objects.values_list("name", flat=True))

    assert {role.value for role in Role} <= names
