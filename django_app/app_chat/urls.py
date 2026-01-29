from django.urls import path
from .views import (
    CreateDirectChatAPIView,
    SendMessageAPIView,
    ReadMessageAPIView,
    UniversalChatsAPIView,
    ConversationMessagesAPIView, TotalUnreadChatsAPIView, TeacherClosedChatsStatsAPIView,
    ConversationTransferAPIView, RequestCloseConversationAPIView, ConfirmCloseAndRateAPIView
)

urlpatterns = [
    path("chat/create-direct/", CreateDirectChatAPIView.as_view()),

    path("chat/list/", UniversalChatsAPIView.as_view()),

    path("chat/<int:conversation_id>/messages/", ConversationMessagesAPIView.as_view()),

    path("chat/<int:conversation_id>/send/", SendMessageAPIView.as_view()),

    path("chat/message/<int:message_id>/read/", ReadMessageAPIView.as_view()),
    path("chats/unread-total/",TotalUnreadChatsAPIView.as_view(),name="total-unread-chats"),
    path("teacher/closed-chats-stats/",TeacherClosedChatsStatsAPIView.as_view(),name="teacher-closed-chats-stats"),
    path("conversation/transfer/", ConversationTransferAPIView.as_view()),
    path("conversation/<int:conversation_id>/request-close/", RequestCloseConversationAPIView.as_view()),
    path("conversation/<int:conversation_id>/confirm-close/", ConfirmCloseAndRateAPIView.as_view()),

]
