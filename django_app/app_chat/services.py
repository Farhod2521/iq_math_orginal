from django.core.exceptions import PermissionDenied
from .models import Conversation, ConversationParticipant, Message


def user_in_conversation(*, conversation_id, user):
    return ConversationParticipant.objects.filter(
        conversation_id=conversation_id,
        user=user,
    ).exists()


def create_message(*, conversation_id, sender, text=None, reply_to_id=None):
    if not user_in_conversation(conversation_id=conversation_id, user=sender):
        raise PermissionDenied("User is not a conversation participant.")

    conversation = Conversation.objects.get(id=conversation_id)
    reply_to = None
    if reply_to_id:
        reply_to = Message.objects.get(id=reply_to_id)

    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        text=text,
        reply_to=reply_to,
    )

    conversation.last_message = text or "File"
    conversation.last_message_at = message.created_at
    conversation.save(update_fields=["last_message", "last_message_at"])

    for part in conversation.participants.exclude(user=sender):
        part.unread_count += 1
        part.save(update_fields=["unread_count"])

    return message
