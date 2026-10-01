import json
from typing import Any

from rest_framework import serializers

from apps.homework.serializers import CODE_LANGUAGES, HomeworkFileSerializer
from apps.quizzes.serializers import QuizQuestionSerializer, QuizResultSerializer

MAX_RESPONSE_CHARS = 5000
EXAM_STATES = [("UPCOMING", "Ochilmagan"), ("OPEN", "Ochiq"), ("CLOSED", "Yopilgan")]


class TaskAnswerSerializer(serializers.Serializer[dict[str, Any]]):
    """Amaliy topshiriq javobi (uy vazifasi javobi bilan bir xil ko'rinish)."""

    id = serializers.IntegerField()
    text = serializers.CharField(allow_blank=True)
    code = serializers.CharField(allow_blank=True)
    language = serializers.CharField(allow_blank=True)
    link = serializers.CharField(allow_blank=True)
    files = HomeworkFileSerializer(many=True)
    updated_at = serializers.DateTimeField()
    score = serializers.IntegerField(allow_null=True)
    feedback = serializers.CharField(allow_blank=True)
    reviewer_name = serializers.CharField(allow_blank=True)
    reviewed_at = serializers.DateTimeField(allow_null=True)


class ExamTaskSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    order = serializers.IntegerField()
    title = serializers.CharField()
    instructions = serializers.CharField()
    answer = TaskAnswerSerializer(allow_null=True)


class ExamTestSerializer(serializers.Serializer[dict[str, Any]]):
    """Test qismi holati. `score` — yakunlangach; `review` — imtihon yopilgach."""

    questions = serializers.IntegerField()
    minutes = serializers.IntegerField()
    started = serializers.BooleanField()
    finished = serializers.BooleanField()
    deadline = serializers.DateTimeField(allow_null=True)
    seconds_left = serializers.IntegerField()
    score = serializers.IntegerField(allow_null=True)
    review = QuizResultSerializer(many=True)
    review_questions = QuizQuestionSerializer(many=True)


class ExamOutcomeSerializer(serializers.Serializer[dict[str, Any]]):
    test_score = serializers.IntegerField()
    practical_score = serializers.IntegerField()
    total = serializers.IntegerField()
    passed = serializers.BooleanField()
    final = serializers.BooleanField(help_text="Yakuniy: imtihon yopilgan va hammasi baholangan.")


class ExamCardSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    course_title = serializers.CharField()
    course_slug = serializers.CharField()
    opens_at = serializers.DateTimeField()
    closes_at = serializers.DateTimeField(help_text="Shu o'quvchi uchun (alohida muddat bilan).")
    state = serializers.ChoiceField(choices=EXAM_STATES)
    can_take = serializers.BooleanField()
    pass_percent = serializers.IntegerField()
    test_weight = serializers.IntegerField()
    tasks_total = serializers.IntegerField()
    tasks_submitted = serializers.IntegerField()
    test = ExamTestSerializer()
    result = ExamOutcomeSerializer(allow_null=True)


class ExamDetailSerializer(ExamCardSerializer):
    tasks = ExamTaskSerializer(many=True)


class ExamSavedSerializer(serializers.Serializer[dict[str, Any]]):
    question = serializers.IntegerField()
    response = serializers.DictField()


class ExamAttemptSerializer(serializers.Serializer[dict[str, Any]]):
    """Test: savollar (javobsiz) va berilgan javoblar (natijasiz)."""

    id = serializers.IntegerField()
    exam_id = serializers.IntegerField()
    total = serializers.IntegerField()
    deadline = serializers.DateTimeField()
    seconds_left = serializers.IntegerField()
    finished = serializers.BooleanField()
    score = serializers.IntegerField(allow_null=True)
    questions = QuizQuestionSerializer(many=True)
    answers = ExamSavedSerializer(many=True)


class ExamAnswerSerializer(serializers.Serializer[dict[str, Any]]):
    question = serializers.IntegerField()
    response = serializers.DictField()

    def validate_response(self, value: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(value, ensure_ascii=False)) > MAX_RESPONSE_CHARS:
            raise serializers.ValidationError("Javob juda uzun.")
        return value


class ExamFinishSerializer(serializers.Serializer[dict[str, Any]]):
    score = serializers.IntegerField()


class TaskSubmitSerializer(serializers.Serializer[dict[str, Any]]):
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


# --- O'qituvchi ---


class TeacherExamSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    course_title = serializers.CharField()
    month = serializers.DateField()
    status = serializers.CharField()
    opens_at = serializers.DateTimeField()
    closes_at = serializers.DateTimeField()
    students = serializers.IntegerField()
    tested = serializers.IntegerField()
    to_grade = serializers.IntegerField()


class TeacherTaskCellSerializer(serializers.Serializer[dict[str, Any]]):
    task_id = serializers.IntegerField()
    answer = TaskAnswerSerializer(allow_null=True)


class TeacherRowSerializer(serializers.Serializer[dict[str, Any]]):
    student_id = serializers.IntegerField()
    name = serializers.CharField()
    group = serializers.CharField(allow_blank=True)
    test_score = serializers.IntegerField(allow_null=True)
    test_started = serializers.BooleanField()
    tasks = TeacherTaskCellSerializer(many=True)
    total = serializers.IntegerField(allow_null=True)
    passed = serializers.BooleanField(allow_null=True)
    final = serializers.BooleanField()
    extension_until = serializers.DateTimeField(allow_null=True)


class TeacherExamDetailSerializer(TeacherExamSerializer):
    pass_percent = serializers.IntegerField()
    test_weight = serializers.IntegerField()
    tasks = ExamTaskSerializer(many=True)
    rows = TeacherRowSerializer(many=True)


class GradeSerializer(serializers.Serializer[dict[str, Any]]):
    score = serializers.IntegerField(min_value=0, max_value=100)
    feedback = serializers.CharField(max_length=3000, required=False, allow_blank=True, default="")


class ExtensionSerializer(serializers.Serializer[dict[str, Any]]):
    student = serializers.IntegerField()
    until = serializers.DateTimeField()
