from django.urls import path

from .views import (
    ExamAttemptAnswerView,
    ExamAttemptFinishView,
    ExamDetailView,
    ExamListView,
    ExamTestView,
    TaskAnswerView,
    TeacherExamDetailView,
    TeacherExamListView,
    TeacherExtensionView,
    TeacherGradeView,
)

urlpatterns = [
    path("exams/", ExamListView.as_view(), name="exams"),
    path("exams/<int:pk>/", ExamDetailView.as_view(), name="exam"),
    path("exams/<int:pk>/test/", ExamTestView.as_view(), name="exam-test"),
    path("exam-attempts/<int:pk>/answers/", ExamAttemptAnswerView.as_view(), name="exam-answer"),
    path("exam-attempts/<int:pk>/finish/", ExamAttemptFinishView.as_view(), name="exam-finish"),
    path("exam-tasks/<int:pk>/answer/", TaskAnswerView.as_view(), name="exam-task-answer"),
    path("teacher/exams/", TeacherExamListView.as_view(), name="teacher-exams"),
    path("teacher/exams/<int:pk>/", TeacherExamDetailView.as_view(), name="teacher-exam"),
    path(
        "teacher/exams/<int:pk>/extensions/",
        TeacherExtensionView.as_view(),
        name="teacher-exam-extension",
    ),
    path("teacher/exam-answers/<int:pk>/grade/", TeacherGradeView.as_view(), name="teacher-grade"),
]
