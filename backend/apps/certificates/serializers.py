from typing import Any

from rest_framework import serializers

REQUIREMENTS = [
    ("lessons", "Darslar"),
    ("quizzes", "Testlar"),
    ("homework", "Uy vazifalari"),
    ("exams", "Imtihonlar o'rtachasi"),
]


class CertificateSerializer(serializers.Serializer[dict[str, Any]]):
    number = serializers.CharField()
    full_name = serializers.CharField()
    course_title = serializers.CharField()
    course_slug = serializers.CharField()
    score = serializers.IntegerField()
    issued_at = serializers.DateTimeField()
    valid = serializers.BooleanField()
    revoked_at = serializers.DateTimeField(allow_null=True)
    revoke_reason = serializers.CharField(allow_blank=True)


class RequirementSerializer(serializers.Serializer[dict[str, Any]]):
    code = serializers.ChoiceField(choices=REQUIREMENTS)
    done = serializers.IntegerField(help_text="exams: o'rtacha foiz")
    total = serializers.IntegerField(help_text="exams: kerakli foiz")
    ok = serializers.BooleanField()


class CourseProgressSerializer(serializers.Serializer[dict[str, Any]]):
    """Sertifikati hali yo'q kurs: nimalar qoldi."""

    course_title = serializers.CharField()
    course_slug = serializers.CharField()
    requirements = RequirementSerializer(many=True)


class MyCertificatesSerializer(serializers.Serializer[dict[str, Any]]):
    certificates = CertificateSerializer(many=True)
    progress = CourseProgressSerializer(many=True)
