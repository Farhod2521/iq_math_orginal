from django.urls import path
from .views import (
    CreateDirectChatAPIView,
    StudentSupportChatMessageAPIView,
    SendMessageAPIView,
    ReadMessageAPIView,
    UniversalChatsAPIView,
    ConversationMessagesAPIView, TotalUnreadChatsAPIView, TeacherClosedChatsStatsAPIView,
    ConversationTransferAPIView, RequestCloseConversationAPIView, ConfirmCloseAndRateAPIView,
    SuperAdminTeachersClosedChatsStatsAPIView
)

urlpatterns = [
    path("chat/create-direct/", CreateDirectChatAPIView.as_view()),
    path("chat/student-support/send/", StudentSupportChatMessageAPIView.as_view()),

    path("chat/list/", UniversalChatsAPIView.as_view()),

    path("chat/<int:conversation_id>/messages/", ConversationMessagesAPIView.as_view()),

    path("chat/<int:conversation_id>/send/", SendMessageAPIView.as_view()),

    path("chat/message/<int:message_id>/read/", ReadMessageAPIView.as_view()),
    path("chats/unread-total/",TotalUnreadChatsAPIView.as_view(),name="total-unread-chats"),
    path("teacher/closed-chats-stats/",TeacherClosedChatsStatsAPIView.as_view(),name="teacher-closed-chats-stats"),
    path("superadmin_by_teacher_stats/closed-chats-stats/",SuperAdminTeachersClosedChatsStatsAPIView.as_view(),name="teacher-closed-chats-stats"),
    path("conversation/transfer/", ConversationTransferAPIView.as_view()),
    path("conversation/<int:conversation_id>/request-close/", RequestCloseConversationAPIView.as_view()),
    path("conversation/<int:conversation_id>/confirm-close/", ConfirmCloseAndRateAPIView.as_view()),

]
