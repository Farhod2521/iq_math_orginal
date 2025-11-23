from rest_framework import serializers
from .models import Conversation, ConversationParticipant, Message, MessageReceipt
from django.contrib.auth import get_user_model

User = get_user_model()


# ---------------- CONVERSATION SERIALIZER ----------------
class ConversationSerializer(serializers.ModelSerializer):
    last_message = serializers.CharField(read_only=True)
    last_message_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "chat_type", "title", "last_message", "last_message_at"]


# --------------- MESSAGE SERIALIZER -----------------
class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.CharField(source="sender.full_name", read_only=True)
    sender_id = serializers.IntegerField(source="sender.id", read_only=True)

    class Meta:
        model = Message
        fields = [
            "id", "conversation", "sender", "sender_id",
            "message_type", "text", "file", "reply_to",
            "is_edited", "is_deleted", "created_at"
        ]
        read_only_fields = ["sender", "sender_id"]





class ConversationListSerializer(serializers.ModelSerializer):
    other_user_name = serializers.SerializerMethodField()
    other_user_id = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "chat_type",
            "last_message",
            "last_message_at",
            "other_user_name",
            "other_user_id",
        ]

    def get_other_user_name(self, obj):
        current_user = self.context["request"].user
        participant = obj.participants.exclude(user=current_user).first()

        if not participant:
            return ""

        other = participant.user

        # Agar qosh taraf Student bo'lsa
        if hasattr(other, "student_profile"):
            return other.student_profile.full_name

        # Agar qosh taraf Teacher bo'lsa
        if hasattr(other, "teacher_profile"):
            return other.teacher_profile.full_name

        # fallback (parent/admin/tutor)
        return other.phone

    def get_other_user_id(self, obj):
        current_user = self.context["request"].user
        participant = obj.participants.exclude(user=current_user).first()
        return participant.user.id if participant else None
