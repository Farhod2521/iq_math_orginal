from django.urls import path
from .views import (
    CreateDirectChatAPIView,
    SendMessageAPIView,
    ReadMessageAPIView,
    UniversalChatsAPIView, RateConversationAPIView,
    ConversationMessagesAPIView,  CloseConversationAPIView, TotalUnreadChatsAPIView, TeacherClosedChatsStatsAPIView,
    ConversationTransferAPIView
)

urlpatterns = [
    path("chat/create-direct/", CreateDirectChatAPIView.as_view()),

    path("chat/list/", UniversalChatsAPIView.as_view()),

    path("chat/<int:conversation_id>/messages/", ConversationMessagesAPIView.as_view()),

    path("chat/<int:conversation_id>/send/", SendMessageAPIView.as_view()),

    path("chat/message/<int:message_id>/read/", ReadMessageAPIView.as_view()),
    path("conversations/<int:conversation_id>/close/", CloseConversationAPIView.as_view(), name="close-conversation"),
    path("conversations/<int:conversation_id>/rate/", RateConversationAPIView.as_view(), name="rate-conversation"),
    path("chats/unread-total/",TotalUnreadChatsAPIView.as_view(),name="total-unread-chats"),
    path("teacher/closed-chats-stats/",TeacherClosedChatsStatsAPIView.as_view(),name="teacher-closed-chats-stats"),
    path("conversation/transfer/", ConversationTransferAPIView.as_view()),
]
