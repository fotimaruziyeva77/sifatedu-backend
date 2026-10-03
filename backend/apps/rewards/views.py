"""Yutuqlar API: hamyon, bugungi topshiriqlar, tarix, reyting, chegirma; o'qituvchi — shtraflar."""

from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

from django.utils import timezone, translation
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.learning.models import Enrollment, StudyGroup
from apps.users import services as user_services
from apps.users.models import User
from apps.users.roles import sees_all

from . import daily, rating, referral, services
from .models import DailyTask, Entry
from .serializers import (
    DiscountStateSerializer,
    PenaltyCancelSerializer,
    PenaltySerializer,
    RatingSerializer,
    RewardHistorySerializer,
    RewardSettingsSerializer,
    RewardsSerializer,
)

HISTORY_PAGE = 30
RULES = (
    "lesson_xp",
    "quiz_xp",
    "homework_xp",
    "attendance_xp",
    "exam_xp",
    "daily_bonus_xp",
    "daily_missed_penalty",
    "absent_penalty",
    "late_penalty",
    "homework_late_penalty",
    "referral_lesson_coins",
    "referral_paid_coins",
    "referral_discount",
    "coupon_percent",
)
PENALTY_DAYS = 30
Kind = DailyTask.Kind


def task_url(task: DailyTask) -> str:
    """Topshiriq qayerda bajariladi: dars sahifasi, vazifa, jadval yoki bot."""
    if task.kind in (Kind.LESSON, Kind.QUIZ, Kind.HOMEWORK) and task.lesson_id and task.course:
        path = f"/dashboard/courses/{task.course.slug}/lessons/{task.lesson_id}"
        return path + {"QUIZ": "#quiz", "HOMEWORK": "#homework"}.get(task.kind, "")
    if task.kind == Kind.LIVE:
        return "/dashboard/schedule"
    if task.kind == Kind.REVIEW:
        from apps.bot.links import bot_url

        return bot_url() or ""
    return ""


def task_payload(task: DailyTask) -> dict[str, Any]:
    return {
        "id": task.pk,
        "kind": task.kind,
        "title": task.title,
        "done": task.done_at is not None,
        "url": task_url(task),
    }


def entry_payload(entry: Entry) -> dict[str, Any]:
    course = str(entry.course.title) if entry.course else ""
    return {
        "id": entry.pk,
        "reason": entry.reason,
        "xp": entry.applied_xp,
        "coins": entry.coins,
        "note": entry.note,
        "course_title": course,
        "created_at": entry.created_at,
        "penalty": entry.is_penalty,
        "canceled": entry.canceled_at is not None,
        "cancel_reason": entry.cancel_reason,
    }


def history(user: Any, page: int) -> tuple[list[dict[str, Any]], int | None]:
    start = (page - 1) * HISTORY_PAGE
    rows = list(
        Entry.objects.filter(user_id=user.pk).select_related("course")[
            start : start + HISTORY_PAGE + 1
        ]
    )
    more = len(rows) > HISTORY_PAGE
    return [entry_payload(entry) for entry in rows[:HISTORY_PAGE]], page + 1 if more else None


class RewardsView(APIView):
    """Hamyon (XP, coin, seriya), bugungi topshiriqlar, kuponlar va oxirgi o'zgarishlar."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: RewardsSerializer}, tags=["rewards"])
    def get(self, request: Request) -> Response:
        from apps.bot import links

        user: User = request.user  # type: ignore[assignment]
        wallet = services.wallet_of(user.pk)
        config = services.settings()
        code = user_services.referral_code(user)
        site = links.base_url()
        coupons = referral.valid_coupons(user).select_related("order")
        items, _next = history(user, 1)
        return Response(
            {
                "xp": wallet.xp,
                "coins": wallet.coins,
                "streak": wallet.streak,
                "best_streak": wallet.best_streak,
                "hidden": wallet.hidden,
                "tasks": [task_payload(task) for task in daily.today(user)],
                "coupons": [
                    {
                        "id": coupon.pk,
                        "percent": coupon.percent,
                        "kind": coupon.kind,
                        "created_at": coupon.created_at,
                        "expires_at": coupon.expires_at,
                        "reserved": coupon.order is not None,
                    }
                    for coupon in coupons
                ],
                "history": items[:10],
                "invite_url": f"{site}/{user.locale or 'uz'}?{urlencode({'ref': code})}",
                "invite_bot_url": links.bot_url(links.REFERRAL_PREFIX + code) or "",
                "invited": user.referrals.count(),
                "rules": {name: getattr(config, name) for name in RULES},
            }
        )


class HistoryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("page", OpenApiTypes.INT, required=False)],
        responses={200: RewardHistorySerializer},
        tags=["rewards"],
    )
    def get(self, request: Request) -> Response:
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1
        items, following = history(request.user, page)
        return Response({"results": items, "next_page": following})


class RewardSettingsView(APIView):
    """ "Reytingda ko'rsatilmasin"."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=RewardSettingsSerializer,
        responses={200: RewardSettingsSerializer},
        tags=["rewards"],
    )
    def patch(self, request: Request) -> Response:
        serializer = RewardSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user: User = request.user  # type: ignore[assignment]
        wallet = services.wallet_of(user.pk)
        wallet.hidden = serializer.validated_data["hidden"]
        wallet.save(update_fields=["hidden", "updated_at"])
        return Response({"hidden": wallet.hidden})


class RatingView(APIView):
    """Reyting: davr (hafta, oy, umumiy) va doira (kurs yoki guruh — o'quvchinikidan)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("period", OpenApiTypes.STR, enum=list(rating.PERIODS)),
            OpenApiParameter("scope", OpenApiTypes.STR, enum=list(rating.SCOPES)),
            OpenApiParameter("id", OpenApiTypes.INT),
        ],
        responses={200: RatingSerializer},
        tags=["rewards"],
    )
    def get(self, request: Request) -> Response:
        user: User = request.user  # type: ignore[assignment]
        period = request.query_params.get("period", "week")
        if period not in rating.PERIODS:
            raise ValidationError({"period": ["week, month yoki all."]})
        with translation.override(user.locale or "uz"):
            options = rating.scopes(user)
        kind = request.query_params.get("scope") or (options[0].kind if options else "")
        raw_id = request.query_params.get("id")
        try:
            pk = int(raw_id) if raw_id else (options[0].id if options else None)
        except ValueError as exc:
            raise ValidationError({"id": ["Butun son bo'lsin."]}) from exc
        payload: dict[str, Any] = {
            "period": period,
            "scope": "",
            "scope_id": None,
            "total": 0,
            "top": [],
            "me": None,
        }
        if kind and pk is not None:
            if not rating.can_view(user, kind, pk):
                raise NotFound
            payload = rating.board(user, kind, pk, period)
        payload["scopes"] = [
            {"kind": scope.kind, "id": scope.id, "title": scope.title} for scope in options
        ]
        return Response(payload)


class DiscountView(APIView):
    """To'lov panelida: foydalanuvchining keyingi to'loviga chegirmasi (bo'lmasa — null).
    Kirmagan mehmonga ham 200 (null): kurs sahifasida konsolda 403 xatosi chiqmasin."""

    permission_classes = [AllowAny]

    @extend_schema(responses={200: DiscountStateSerializer}, tags=["rewards"])
    def get(self, request: Request) -> Response:
        discount = referral.discount_for(request.user)
        if discount is None:
            return Response({"discount": None})
        return Response({"discount": {"percent": discount.percent, "reason": discount.reason}})


# --- O'qituvchi ---


def penalties_for(user: Any, group_id: int | None) -> list[Entry]:
    since = timezone.now() - timedelta(days=PENALTY_DAYS)
    entries = Entry.objects.filter(reason__in=Entry.PENALTIES, created_at__gte=since)
    if group_id is not None:
        group = get_object_or_404(StudyGroup, pk=group_id)
        if not (sees_all(user) or group.teacher_id == user.pk):
            raise NotFound
        students = Enrollment.objects.filter(group=group).values("user_id")
        entries = entries.filter(user_id__in=students)
    elif not sees_all(user):
        groups = StudyGroup.objects.filter(teacher=user).values("pk")
        entries = entries.filter(
            user_id__in=Enrollment.objects.filter(group__in=groups).values("user_id")
        )
    return list(entries.select_related("user").order_by("-created_at")[:200])


def penalty_payload(entry: Entry, viewer: Any) -> dict[str, Any]:
    return {
        "id": entry.pk,
        "student_id": entry.user_id,
        "student_name": entry.user.get_full_name() or entry.user.phone,
        "reason": entry.reason,
        "xp": entry.applied_xp,
        "note": entry.note,
        "created_at": entry.created_at,
        "canceled": entry.canceled_at is not None,
        "cancel_reason": entry.cancel_reason,
        "can_cancel": services.can_cancel(viewer, entry),
    }


class PenaltyListView(APIView):
    """Oxirgi 30 kundagi shtraflar: o'qituvchiga — o'z guruhlari, adminga — hammasi."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("group", OpenApiTypes.INT, required=False)],
        responses={200: PenaltySerializer(many=True)},
        tags=["rewards"],
    )
    def get(self, request: Request) -> Response:
        user: User = request.user  # type: ignore[assignment]
        if not (sees_all(user) or user.is_staff):
            raise PermissionDenied
        raw = request.query_params.get("group")
        group_id = int(raw) if raw and raw.isdigit() else None
        return Response([penalty_payload(entry, user) for entry in penalties_for(user, group_id)])


class PenaltyCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=PenaltyCancelSerializer, responses={200: PenaltySerializer}, tags=["rewards"]
    )
    def post(self, request: Request, pk: int) -> Response:
        user: User = request.user  # type: ignore[assignment]
        entry = get_object_or_404(Entry.objects.select_related("user"), pk=pk)
        if not services.can_cancel(user, entry):
            raise NotFound
        serializer = PenaltyCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            entry = services.cancel(entry, by=user, reason=serializer.validated_data["reason"])
        except services.RewardError as exc:
            raise ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(penalty_payload(entry, user))
