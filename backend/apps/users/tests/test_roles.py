"""Rollar: guruhlar va ruxsatlar jadvali, `is_staff` avtomatikasi, rol berish buyrug'i."""

import io
from typing import Any

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.users.models import User
from apps.users.roles import Role, role_names, set_roles, sync_role_groups

pytestmark = pytest.mark.django_db


def make_user(phone: str, *roles: str) -> User:
    user = User.objects.create_user(phone=phone, password="Str0ng-pass")
    set_roles(user, roles)
    user.refresh_from_db()
    return user


def test_groups_follow_the_table() -> None:
    sync_role_groups()

    teacher = Group.objects.get(name=Role.TEACHER)
    director = Group.objects.get(name=Role.DIRECTOR)
    perms = {f"{p.content_type.app_label}.{p.codename}" for p in teacher.permissions.all()}
    assert {"catalog.add_lesson", "catalog.add_lessonmaterial", "videos.add_videoasset"} <= perms
    assert "catalog.change_course" not in perms
    assert "leads.view_lead" not in perms
    assert director.permissions.exclude(codename__startswith="view_").count() == 0
    assert director.permissions.filter(codename="view_lead").exists()
    assert not Group.objects.get(name=Role.STUDENT).permissions.exists()


def test_staff_access_follows_roles() -> None:
    user = make_user("+998901000001", Role.STUDENT)
    assert not user.is_staff

    set_roles(user, [Role.STUDENT, Role.TEACHER])
    user.refresh_from_db()
    assert user.is_staff and role_names(user) == {Role.STUDENT, Role.TEACHER}

    set_roles(user, [Role.STUDENT])
    user.refresh_from_db()
    assert not user.is_staff


def test_other_groups_are_kept_and_superuser_stays_staff() -> None:
    custom = Group.objects.create(name="Hamkorlar")
    admin = User.objects.create_superuser(phone="+998901000002", password="Str0ng-pass")
    admin.groups.add(custom)

    set_roles(admin, [])
    admin.refresh_from_db()

    assert admin.is_staff and admin.groups.filter(name="Hamkorlar").exists()
    assert Role.ADMIN in role_names(admin)


def test_role_permissions_work(settings: Any) -> None:
    teacher = make_user("+998901000003", Role.TEACHER)
    director = make_user("+998901000004", Role.DIRECTOR)

    assert teacher.has_perm("catalog.change_lesson")
    assert not teacher.has_perm("catalog.change_course")
    assert director.has_perm("payments.view_order")
    assert not director.has_perm("payments.change_order")


def test_grant_role_command() -> None:
    make_user("+998901000005", Role.STUDENT)
    out = io.StringIO()

    call_command("grant_role", "90 100 00 05", Role.MANAGER, stdout=out)

    user = User.objects.get(phone="+998901000005")
    assert user.is_staff and role_names(user) == {Role.STUDENT, Role.MANAGER}
    assert "Menejer" in out.getvalue()

    call_command("grant_role", "+998901000005", Role.MANAGER, "--remove", stdout=io.StringIO())
    user.refresh_from_db()
    assert not user.is_staff


def test_me_includes_roles() -> None:
    client = APIClient()
    client.force_authenticate(make_user("+998901000006", Role.STUDENT, Role.TEACHER))

    assert client.get("/api/v1/me/").json()["roles"] == [Role.STUDENT, Role.TEACHER]
