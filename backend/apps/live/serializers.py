from typing import Any

from rest_framework import serializers

from .models import Attendance, LiveLesson

MAX_ITEMS = 300


class LiveLessonSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    group_id = serializers.IntegerField()
    group = serializers.CharField()
    course_title = serializers.CharField()
    course_slug = serializers.CharField()
    title = serializers.CharField(allow_blank=True, help_text="Sarlavha yoki mavzu (dars nomi).")
    kind = serializers.ChoiceField(choices=LiveLesson.Kind.choices)
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    opens_at = serializers.DateTimeField(help_text='Shu vaqtdan "Qo\'shilish" ochiladi.')
    duration_min = serializers.IntegerField()
    room = serializers.CharField(allow_blank=True)
    notes = serializers.CharField(allow_blank=True)
    canceled = serializers.BooleanField()
    cancel_reason = serializers.CharField(allow_blank=True)
    join_url = serializers.CharField(
        allow_blank=True, help_text="Onlayn dars: platforma orqali Meet'ga yo'naltiradi."
    )
    can_join = serializers.BooleanField(help_text="Hozir qo'shilish mumkin.")
    recording_url = serializers.CharField(allow_blank=True, help_text="Faqat tugagan darsda.")
    attendance = serializers.ChoiceField(
        choices=Attendance.Status.choices,
        allow_null=True,
        help_text="O'quvchining shu darsdagi holati (o'qituvchiga — null).",
    )
    is_teacher = serializers.BooleanField()


class RosterItemSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    name = serializers.CharField()
    avatar = serializers.CharField(allow_blank=True)
    status = serializers.ChoiceField(choices=Attendance.Status.choices, allow_blank=True)
    joined_at = serializers.DateTimeField(allow_null=True)


class CourseLessonSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    title = serializers.CharField()
    module = serializers.CharField()
    covered = serializers.BooleanField(help_text="Guruhda o'tilgan (vazifalari ochiq).")


class TeacherLiveSerializer(LiveLessonSerializer):
    meet_url = serializers.CharField(allow_blank=True)
    topic_id = serializers.IntegerField(allow_null=True, help_text="Mavzu — kurs darsi.")
    covered = serializers.BooleanField(help_text="Mavzu guruhda o'tilgan deb belgilangan.")
    can_uncover = serializers.BooleanField(
        help_text="Belgi shu darsdan qo'yilgan — qaytarish mumkin."
    )
    course_lessons = CourseLessonSerializer(many=True)
    can_mark = serializers.BooleanField(help_text="Davomatni belgilash mumkin (dars boshlangan).")
    can_cancel = serializers.BooleanField(help_text="Dars hali boshlanmagan.")
    students = RosterItemSerializer(many=True)


class AttendanceItemSerializer(serializers.Serializer[dict[str, Any]]):
    student = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Attendance.Status.choices)


class AttendanceSaveSerializer(serializers.Serializer[dict[str, Any]]):
    items = AttendanceItemSerializer(many=True, allow_empty=False)

    def validate_items(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(value) > MAX_ITEMS:
            raise serializers.ValidationError("Ro'yxat juda uzun.")
        return value


class CoverSerializer(serializers.Serializer[dict[str, Any]]):
    lesson = serializers.IntegerField(help_text="O'tilgan kurs darsi.")


class CancelSerializer(serializers.Serializer[dict[str, Any]]):
    reason = serializers.CharField(max_length=200, allow_blank=True, required=False, default="")


class LiveUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    recording_url = serializers.URLField(allow_blank=True, required=False, max_length=200)
    notes = serializers.CharField(allow_blank=True, required=False, max_length=2000)
