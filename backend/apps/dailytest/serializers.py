from typing import Any

from rest_framework import serializers

from apps.quizzes.serializers import QuizQuestionSerializer, QuizResultSerializer

from .models import DailyTest

# O'qituvchi jadvalida o'quvchi holati: tugatdi, boshladi, ishlamadi.
STUDENT_STATUSES = [("DONE", "Tugatdi"), ("STARTED", "Boshladi"), ("NONE", "Ishlamadi")]
# Kun bo'yicha: test yo'q bo'lsa — NONE.
DAY_STATUSES = [*DailyTest.Status.choices, ("NONE", "Test yo'q")]


class DailyRowSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField()
    correct = serializers.IntegerField()
    total = serializers.IntegerField()
    me = serializers.BooleanField()


class DailyAttemptBriefSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    correct = serializers.IntegerField()
    total = serializers.IntegerField()
    finished = serializers.BooleanField()
    reviewable = serializers.BooleanField(help_text="To'g'ri javoblar ochiqmi (test yopilgach).")


class DailyTodaySerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    day = serializers.DateField()
    status = serializers.ChoiceField(choices=DailyTest.Status.choices)
    questions_count = serializers.IntegerField()
    opens_at = serializers.DateTimeField()
    closes_at = serializers.DateTimeField()
    open = serializers.BooleanField(help_text="Hozir ishlash mumkinmi.")
    attempt = DailyAttemptBriefSerializer(allow_null=True)


class DailyHistorySerializer(serializers.Serializer[dict[str, Any]]):
    attempt_id = serializers.IntegerField()
    day = serializers.DateField()
    correct = serializers.IntegerField()
    total = serializers.IntegerField()
    reviewable = serializers.BooleanField()


class DailyGroupSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    name = serializers.CharField()
    course = serializers.CharField()
    today = DailyTodaySerializer(allow_null=True)
    day_rating = DailyRowSerializer(many=True)
    week_rating = DailyRowSerializer(many=True)
    history = DailyHistorySerializer(many=True)


class DailyOverviewSerializer(serializers.Serializer[dict[str, Any]]):
    enabled = serializers.BooleanField()
    bot_url = serializers.CharField(allow_blank=True, help_text="Testni botda ochadigan havola.")
    groups = DailyGroupSerializer(many=True)


class DailyReviewSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    day = serializers.DateField()
    group = serializers.CharField()
    correct = serializers.IntegerField()
    total = serializers.IntegerField()
    review = QuizResultSerializer(many=True)
    review_questions = QuizQuestionSerializer(many=True)


class TeacherDailyRowSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.ChoiceField(choices=STUDENT_STATUSES)
    correct = serializers.IntegerField(allow_null=True)
    total = serializers.IntegerField(allow_null=True)
    finished_at = serializers.DateTimeField(allow_null=True)


class TeacherDailyDaySerializer(serializers.Serializer[dict[str, Any]]):
    day = serializers.DateField()
    status = serializers.ChoiceField(choices=DailyTest.Status.choices)
    done = serializers.IntegerField()


class TeacherDailySerializer(serializers.Serializer[dict[str, Any]]):
    day = serializers.DateField()
    status = serializers.ChoiceField(choices=DAY_STATUSES)
    questions_count = serializers.IntegerField()
    pool_size = serializers.IntegerField(help_text="O'tilgan darslar testlaridagi savollar.")
    done = serializers.IntegerField()
    students = TeacherDailyRowSerializer(many=True)
    recent = TeacherDailyDaySerializer(many=True, help_text="Oxirgi 7 ta test kuni.")
