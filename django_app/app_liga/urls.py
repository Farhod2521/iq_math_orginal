from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CurrentSeasonAPIView, JoinSeasonAPIView, WinnersHistoryAPIView, StartTestAPIView, AttemptDetailAPIView,
    AttemptAnswerAPIView, AttemptFinishAPIView, AdminMetaAPIView, AdminSeasonViewSet, AdminTestViewSet,
    AdminQuestionViewSet, AdminWinnerViewSet,
)

router = DefaultRouter()
router.register("seasons", AdminSeasonViewSet, basename="liga-admin-season")
router.register("tests", AdminTestViewSet, basename="liga-admin-test")
router.register("questions", AdminQuestionViewSet, basename="liga-admin-question")
router.register("winners", AdminWinnerViewSet, basename="liga-admin-winner")

urlpatterns = [
    # O'quvchi
    path("current/", CurrentSeasonAPIView.as_view()),
    path("winners/", WinnersHistoryAPIView.as_view()),
    path("seasons/<int:season_id>/join/", JoinSeasonAPIView.as_view()),
    path("tests/<int:test_id>/start/", StartTestAPIView.as_view()),
    path("attempts/<int:attempt_id>/", AttemptDetailAPIView.as_view()),
    path("attempts/<int:attempt_id>/answer/", AttemptAnswerAPIView.as_view()),
    path("attempts/<int:attempt_id>/finish/", AttemptFinishAPIView.as_view()),
    # Mentor / admin
    path("admin/meta/", AdminMetaAPIView.as_view()),
    path("admin/", include(router.urls)),
]
