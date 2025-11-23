from django.urls import path
from .views import (
    CreateDirectChatAPIView,
    SendMessageAPIView,
    ReadMessageAPIView,
    TeacherChatsAPIView,
    ConversationMessagesAPIView,
)

urlpatterns = [
    # Chat yaratish
    path("chat/create-direct/", CreateDirectChatAPIView.as_view(), name="create-direct-chat"),

    # Teacher uchun chatlar listi
    path("chat/teacher/", TeacherChatsAPIView.as_view(), name="teacher-chats"),

    # Chat ichidagi xabarlar
    path("chat/<int:conversation_id>/messages/", ConversationMessagesAPIView.as_view(), name="conversation-messages"),

    # Xabar yuborish
    path("chat/<int:conversation_id>/send/", SendMessageAPIView.as_view(), name="chat-send-message"),

    # Xabarni o‘qilgan deb belgilash
    path("chat/message/<int:message_id>/read/", ReadMessageAPIView.as_view(), name="read-message"),
]
