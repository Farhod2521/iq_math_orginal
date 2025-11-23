from django.urls import path
from .views import (
    CreateDirectChatAPIView,
    SendMessageAPIView,
    ReadMessageAPIView, ConversationListAPIView
)

urlpatterns = [
    # 1) Student ↔ Teacher o‘rtasida direct chat yaratish
    path("chat/create-direct/", CreateDirectChatAPIView.as_view(), name="create-direct-chat"),

    # 2) Chatga xabar yuborish
    path("chat/<int:conversation_id>/send/", SendMessageAPIView.as_view(), name="chat-send-message"),

    # 3) Xabarni o‘qilgan deb belgilash
    path("chat/message/<int:message_id>/read/", ReadMessageAPIView.as_view(), name="read-message"),

    path("conversations/", ConversationListAPIView.as_view(), name="conversation-list"),
]
