import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .services import create_message, user_in_conversation

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            logger.warning("WS reject unauthenticated conversation_id=%s", self.conversation_id)
            await self.close()
            return

        allowed = await database_sync_to_async(user_in_conversation)(
            conversation_id=self.conversation_id,
            user=user,
        )
        if not allowed:
            logger.warning("WS reject not participant user_id=%s conversation_id=%s", user.id, self.conversation_id)
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        text = data.get("text")
        reply_to_id = data.get("reply_to")
        if not text and not reply_to_id:
            return

        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            return

        try:
            message = await database_sync_to_async(create_message)(
                conversation_id=self.conversation_id,
                sender=user,
                text=text,
                reply_to_id=reply_to_id,
            )
        except Exception:
            return

        sender_name = (
            getattr(message.sender, "full_name", None)
            or getattr(message.sender, "get_full_name", lambda: "")()
            or str(message.sender)
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "message": {
                    "id": message.id,
                    "text": message.text,
                    "sender_id": message.sender_id,
                    "sender_name": sender_name,
                    "created_at": message.created_at.isoformat(),
                },
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))
