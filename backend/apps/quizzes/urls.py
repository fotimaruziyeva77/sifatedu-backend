from django.urls import path

from .views import AttemptAnswerView, AttemptFinishView, QuizStartView

urlpatterns = [
    path("quizzes/<int:pk>/attempts/", QuizStartView.as_view(), name="quiz-start"),
    path("quiz-attempts/<int:pk>/answers/", AttemptAnswerView.as_view(), name="quiz-answer"),
    path("quiz-attempts/<int:pk>/finish/", AttemptFinishView.as_view(), name="quiz-finish"),
]
