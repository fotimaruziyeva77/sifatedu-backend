"""Kunlik test saytda: o'quvchi — bugungi holat, guruh reytingi, tarix va javoblar (test
yopilgach); o'qituvchi — guruhda kim ishladi va kim ishlamadi. Testning o'zi botda ishlanadi."""

from datetime import datetime
from typing import Any

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bot import links
from apps.learning.models import StudyGroup
from apps.learning.teaching import IsTeacher, teacher_groups
from apps.live.services import members, student_group_ids
from apps.quizzes.services import Layout, load_questions
from apps.rewards import services as rewards
from apps.rewards.rating import short_name
from apps.users.models import User

from . import services
from .models import DailyAttempt, DailyTest
from .serializers import DailyOverviewSerializer, DailyReviewSerializer, TeacherDailySerializer

HISTORY = 14
RECENT_DAYS = 7


def rows(found: list[services.Row], user: User) -> list[dict[str, Any]]:
    return [
        {
            "name": row.name,
            "correct": row.correct,
            "total": row.total,
            "me": row.student_id == user.pk,
        }
        for row in found
    ]


def brief(attempt: DailyAttempt, now: datetime) -> dict[str, Any]:
    return {
        "id": attempt.pk,
        "correct": attempt.correct,
        "total": attempt.total,
        "finished": attempt.finished_at is not None,
        "reviewable": services.can_review(attempt, now=now),
    }


def group_overview(group: StudyGroup, user: User, now: datetime) -> dict[str, Any]:
    day = services.local_day(now)
    test = DailyTest.objects.filter(group=group, day=day).first()
    today = None
    if test is not None and test.status != DailyTest.Status.SKIPPED:
        attempt = test.attempts.filter(student=user).first()
        today = {
            "id": test.pk,
            "day": test.day,
            "status": test.status,
            "questions_count": test.questions_count,
            "opens_at": test.opens_at,
            "closes_at": test.closes_at,
            "open": services.is_open(test, now),
            "attempt": brief(attempt, now) if attempt is not None else None,
        }
    history = (
        DailyAttempt.objects.filter(student=user, test__group=group, finished_at__isnull=False)
        .select_related("test")
        .order_by("-test__day")[:HISTORY]
    )
    return {
        "id": group.pk,
        "name": group.name,
        "course": str(group.course.title),
        "today": today,
        "day_rating": rows(services.day_rating(test), user) if test is not None else [],
        "week_rating": rows(services.week_rating(group, day), user),
        "history": [
            {
                "attempt_id": attempt.pk,
                "day": attempt.test.day,
                "correct": attempt.correct,
                "total": attempt.total,
                "reviewable": services.can_review(attempt, now=now),
            }
            for attempt in history
        ],
    }


class DailyOverviewView(APIView):
    """O'quvchining guruhlari: bugungi test, kunlik va haftalik reyting, oxirgi natijalar."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=DailyOverviewSerializer, tags=["daily-test"])
    def get(self, request: Request) -> Response:
        user: User = request.user  # type: ignore[assignment]
        now = timezone.now()
        groups = (
            StudyGroup.objects.filter(pk__in=student_group_ids(user))
            .select_related("course")
            .order_by("pk")
        )
        return Response(
            {
                "enabled": rewards.settings().daily_test,
                "bot_url": links.bot_url("dt") or "",
                "groups": [group_overview(group, user, now) for group in groups],
            }
        )


class DailyReviewView(APIView):
    """Javoblar va izohlar — faqat o'z urinishi va test yopilgach (23:00 dan keyin)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=DailyReviewSerializer, tags=["daily-test"])
    def get(self, request: Request, pk: int) -> Response:
        attempt = get_object_or_404(
            DailyAttempt.objects.select_related("test__group"), pk=pk, student=request.user
        )
        if not services.can_review(attempt):
            raise PermissionDenied(_("To'g'ri javoblar test yopilgach — 23:00 dan keyin ochiladi."))
        questions = load_questions(attempt.question_ids)
        return Response(
            {
                "id": attempt.pk,
                "day": attempt.test.day,
                "group": attempt.test.group.name,
                "correct": attempt.correct,
                "total": attempt.total,
                "review": services.review(attempt),
                "review_questions": [
                    Layout.build(questions[question_id], attempt.seed).payload()
                    for question_id in attempt.question_ids
                    if question_id in questions
                ],
            }
        )


STATUS_ORDER = {"NONE": 0, "STARTED": 1, "DONE": 2}


class TeacherDailyView(APIView):
    """Guruhning kunlik testi: kim ishladi (natijasi bilan) va kim ishlamadi."""

    permission_classes = [IsAuthenticated, IsTeacher]

    @extend_schema(
        parameters=[OpenApiParameter("day", OpenApiTypes.DATE, required=False)],
        responses=TeacherDailySerializer,
        tags=["teacher"],
    )
    def get(self, request: Request, pk: int) -> Response:
        group = get_object_or_404(teacher_groups(request.user), pk=pk)
        day = parse_date(str(request.query_params.get("day") or "")) or services.local_day()
        test = DailyTest.objects.filter(group=group, day=day).first()
        attempts = {attempt.student_id: attempt for attempt in test.attempts.all()} if test else {}
        students: list[dict[str, Any]] = []
        for student in members(group.pk):
            attempt = attempts.get(student.pk)
            status = "NONE"
            if attempt is not None:
                status = "DONE" if attempt.finished_at is not None else "STARTED"
            students.append(
                {
                    "id": student.pk,
                    "name": f"{student.first_name} {student.last_name}".strip()
                    or short_name(student),
                    "status": status,
                    "correct": attempt.correct if attempt and attempt.finished_at else None,
                    "total": attempt.total if attempt and attempt.finished_at else None,
                    "finished_at": attempt.finished_at if attempt else None,
                }
            )
        # Avval ishlamaganlar (o'qituvchi ular bilan bog'lanadi), keyin natija bo'yicha.
        students.sort(key=lambda row: (STATUS_ORDER[str(row["status"])], -int(row["correct"] or 0)))
        recent = (
            DailyTest.objects.filter(group=group)
            .annotate(done=Count("attempts", filter=Q(attempts__finished_at__isnull=False)))
            .order_by("-day")[:RECENT_DAYS]
        )
        return Response(
            {
                "day": day,
                "status": test.status if test else "NONE",
                "questions_count": test.questions_count if test else 0,
                "pool_size": test.pool_size if test else len(services.pool(group)),
                "done": sum(1 for row in students if row["status"] == "DONE"),
                "students": students,
                "recent": [
                    {"day": item.day, "status": item.status, "done": item.done} for item in recent
                ],
            }
        )
