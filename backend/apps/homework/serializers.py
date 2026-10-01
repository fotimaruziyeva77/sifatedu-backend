from typing import Any

from rest_framework import serializers

from .models import Submission

# O'quvchi uchun yana bir holat: hali javob yubormagan.
HOMEWORK_STATUSES = [("NOT_SUBMITTED", "Topshirilmagan"), *Submission.Status.choices]
CODE_LANGUAGES = [
    "html",
    "css",
    "javascript",
    "typescript",
    "python",
    "sql",
    "java",
    "cpp",
    "other",
]


class HomeworkFileSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    name = serializers.CharField()
    size = serializers.IntegerField()
    is_image = serializers.BooleanField()
    url = serializers.CharField(
        help_text="Qisqa muddatli havola (rasm — sahifada, fayl — yuklab olish)."
    )


class SubmissionSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    attempt = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Submission.Status.choices)
    text = serializers.CharField(allow_blank=True)
    code = serializers.CharField(allow_blank=True)
    language = serializers.CharField(allow_blank=True)
    link = serializers.CharField(allow_blank=True)
    late = serializers.BooleanField()
    files = HomeworkFileSerializer(many=True)
    created_at = serializers.DateTimeField()
    score = serializers.IntegerField(allow_null=True)
    feedback = serializers.CharField(allow_blank=True)
    reviewer_name = serializers.CharField(allow_blank=True)
    reviewed_at = serializers.DateTimeField(allow_null=True)


class HomeworkSerializer(serializers.Serializer[dict[str, Any]]):
    """Dars sahifasidagi vazifa va o'quvchining urinishlari (eng yangisi birinchi)."""

    id = serializers.IntegerField()
    title = serializers.CharField()
    instructions = serializers.CharField()
    deadline = serializers.DateTimeField(allow_null=True)
    status = serializers.ChoiceField(choices=HOMEWORK_STATUSES)
    attempts = SubmissionSerializer(many=True)


class SubmitSerializer(serializers.Serializer[dict[str, Any]]):
    """Javob: izoh, kod, havola va fayllar (`files` — bir nechta, multipart)."""

    text = serializers.CharField(max_length=5000, required=False, allow_blank=True, default="")
    code = serializers.CharField(
        max_length=50000, required=False, allow_blank=True, default="", trim_whitespace=False
    )
    language = serializers.ChoiceField(
        choices=CODE_LANGUAGES, required=False, allow_blank=True, default=""
    )
    link = serializers.URLField(max_length=500, required=False, allow_blank=True, default="")
    files = serializers.ListField(
        child=serializers.FileField(), required=False, default=list, max_length=10
    )


class MyHomeworkItemSerializer(serializers.Serializer[dict[str, Any]]):
    assignment_id = serializers.IntegerField()
    title = serializers.CharField()
    lesson_id = serializers.IntegerField()
    lesson_title = serializers.CharField()
    course_slug = serializers.CharField()
    course_title = serializers.CharField()
    deadline = serializers.DateTimeField(allow_null=True)
    status = serializers.ChoiceField(choices=HOMEWORK_STATUSES)
    score = serializers.IntegerField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)
    position = serializers.IntegerField(help_text="Kurs ichidagi dars tartibi.")


class ReviewCardSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    student_phone = serializers.CharField()
    group_name = serializers.CharField(allow_blank=True)
    course_title = serializers.CharField()
    lesson_title = serializers.CharField()
    assignment_title = serializers.CharField()
    attempt = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Submission.Status.choices)
    late = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    score = serializers.IntegerField(allow_null=True)
    reviewed_at = serializers.DateTimeField(allow_null=True)
    preview = serializers.CharField(allow_blank=True)
    files_count = serializers.IntegerField()


class ReviewGroupSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    name = serializers.CharField()


class ReviewListSerializer(serializers.Serializer[dict[str, Any]]):
    results = ReviewCardSerializer(many=True)
    groups = ReviewGroupSerializer(many=True, help_text="Filtr uchun: o'qituvchining guruhlari.")
    pending = serializers.IntegerField()


class ReviewDetailSerializer(ReviewCardSerializer):
    lesson_id = serializers.IntegerField()
    course_slug = serializers.CharField()
    instructions = serializers.CharField()
    deadline = serializers.DateTimeField(allow_null=True)
    submission = SubmissionSerializer()
    history = SubmissionSerializer(many=True, help_text="Shu vazifa bo'yicha oldingi urinishlar.")
    next_id = serializers.IntegerField(allow_null=True, help_text="Navbatdagi keyingi javob.")


class ReviewDecisionSerializer(serializers.Serializer[dict[str, Any]]):
    decision = serializers.ChoiceField(choices=["accept", "return"])
    score = serializers.IntegerField(min_value=0, max_value=100, required=False, allow_null=True)
    feedback = serializers.CharField(max_length=5000, required=False, allow_blank=True, default="")
