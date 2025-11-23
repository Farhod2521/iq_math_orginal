from django.urls import path
from .views import (
    CreateDirectChatAPIView,
    SendMessageAPIView,
    ReadMessageAPIView,
    UniversalChatsAPIView,
    ConversationMessagesAPIView,
)

urlpatterns = [
    path("chat/create-direct/", CreateDirectChatAPIView.as_view()),

    path("chat/list/", UniversalChatsAPIView.as_view()),

    path("chat/<int:conversation_id>/messages/", ConversationMessagesAPIView.as_view()),

    path("chat/<int:conversation_id>/send/", SendMessageAPIView.as_view()),

    path("chat/message/<int:message_id>/read/", ReadMessageAPIView.as_view()),
]
