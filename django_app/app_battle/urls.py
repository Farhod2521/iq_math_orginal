from django.urls import path
from .views import (
    CreateRoomAPIView, JoinRoomAPIView, RoomDetailAPIView, CancelRoomAPIView,
    MyRatingAPIView, LeaderboardAPIView, HistoryAPIView, EloHistoryAPIView,
)

urlpatterns = [
    path("rooms/create/", CreateRoomAPIView.as_view()),
    path("rooms/join/", JoinRoomAPIView.as_view()),
    path("rooms/<int:room_id>/", RoomDetailAPIView.as_view()),
    path("rooms/<int:room_id>/cancel/", CancelRoomAPIView.as_view()),
    path("rating/me/", MyRatingAPIView.as_view()),
    path("leaderboard/", LeaderboardAPIView.as_view()),
    path("history/", HistoryAPIView.as_view()),
    path("elo-history/", EloHistoryAPIView.as_view()),
]
