from django.urls import path

from .views import (
    AttemptAnswerView,
    AttemptFinishView,
    QuizStartView,
    TeacherDraftCreateView,
    TeacherDraftPublishView,
    TeacherDraftView,
)

urlpatterns = [
    path("quizzes/<int:pk>/attempts/", QuizStartView.as_view(), name="quiz-start"),
    path("quiz-attempts/<int:pk>/answers/", AttemptAnswerView.as_view(), name="quiz-answer"),
    path("quiz-attempts/<int:pk>/finish/", AttemptFinishView.as_view(), name="quiz-finish"),
    path(
        "teacher/live/<int:pk>/quiz-drafts/",
        TeacherDraftCreateView.as_view(),
        name="teacher-quiz-draft-create",
    ),
    path("teacher/quiz-drafts/<int:pk>/", TeacherDraftView.as_view(), name="teacher-quiz-draft"),
    path(
        "teacher/quiz-drafts/<int:pk>/publish/",
        TeacherDraftPublishView.as_view(),
        name="teacher-quiz-draft-publish",
    ),
]
