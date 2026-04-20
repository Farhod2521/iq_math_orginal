from rest_framework import serializers
from .models import Conversation, ConversationParticipant, Message, MessageReceipt, ConversationRating
from django.contrib.auth import get_user_model
from django_app.app_student.models import TopicHelpRequestIndependent
from django_app.app_user.models import Teacher
User = get_user_model()





class ConfirmCloseAndRateSerializer(serializers.Serializer):
    stars = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True)


def get_user_display_name(user):
    if not user:
        return None
    if hasattr(user, "student_profile"):
        return user.student_profile.full_name
    if hasattr(user, "teacher_profile"):
        return user.teacher_profile.full_name
    if hasattr(user, "tutor_profile"):
        return user.tutor_profile.full_name
    return user.phone


class ConversationRatingSerializer(serializers.ModelSerializer):
    conversation_id = serializers.IntegerField(source="conversation.id", read_only=True)
    student_id = serializers.IntegerField(source="student.id", read_only=True)
    student_name = serializers.SerializerMethodField()
    mentor_id = serializers.IntegerField(source="mentor.id", read_only=True)
    mentor_name = serializers.SerializerMethodField()

    class Meta:
        model = ConversationRating
        fields = [
            "id",
            "conversation_id",
            "student_id",
            "student_name",
            "mentor_id",
            "mentor_name",
            "stars",
            "comment",
            "created_at",
        ]
        read_only_fields = fields

    def get_student_name(self, obj):
        return get_user_display_name(obj.student)

    def get_mentor_name(self, obj):
        return get_user_display_name(obj.mentor)


class ConversationMetaMixin(serializers.Serializer):
    close_requested_by_id = serializers.SerializerMethodField()
    close_requested_by_name = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()

    def get_close_requested_by_id(self, obj):
        return obj.close_requested_by_id

    def get_close_requested_by_name(self, obj):
        return get_user_display_name(obj.close_requested_by)

    def get_rating(self, obj):
        prefetched_ratings = getattr(obj, "_prefetched_objects_cache", {}).get("ratings")
        if prefetched_ratings is not None:
            rating = prefetched_ratings[0] if prefetched_ratings else None
            if not rating:
                return None
            return ConversationRatingSerializer(rating).data

        rating = (
            obj.ratings
            .select_related("student", "mentor")
            .order_by("-created_at")
            .first()
        )
        if not rating:
            return None
        return ConversationRatingSerializer(rating).data

class TeacherListSerializer(serializers.ModelSerializer):


    class Meta:
        model = Teacher
        fields = (
            "id",
            "full_name",
            "support",
        )


class ConversationTransferSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField()
    teacher_id = serializers.IntegerField()
    reason = serializers.CharField(required=False, allow_blank=True)


# ---------------- CONVERSATION SERIALIZER ----------------
class ConversationSerializer(ConversationMetaMixin, serializers.ModelSerializer):
    last_message = serializers.CharField(read_only=True)
    last_message_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id", "chat_type", "title",
            "last_message", "last_message_at",
            "is_closed", "closed_at",
            "is_close_requested",
            "close_requested_at",
            "close_requested_by_id",
            "close_requested_by_name",
            "rating",
        ]


# --------------- MESSAGE SERIALIZER -----------------
class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_id = serializers.IntegerField(source="sender.id", read_only=True)
    is_read = serializers.SerializerMethodField()

    reply_to_text = serializers.SerializerMethodField()
    reply_to_sender = serializers.SerializerMethodField()

    # 🔥 YANGI QO‘SHIMCHA
    independent_data = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation",
            "sender_id",
            "sender_name",
            "message_type",
            "text",
            "url",
            "file",
            "reply_to",
            "reply_to_text",
            "reply_to_sender",
            "is_edited",
            "is_deleted",
            "created_at",
            "is_read",

            # 🔥 YANGI FIELD
            "independent",
            "independent_data",
        ]

    # ---------------------- OLD METHODS ----------------------

    def get_sender_name(self, obj):
        u = obj.sender
        if hasattr(u, "student_profile"):
            return u.student_profile.full_name
        if hasattr(u, "teacher_profile"):
            return u.teacher_profile.full_name
        return u.phone

    def get_is_read(self, obj):
        user = self.context["request"].user
        receipt = MessageReceipt.objects.filter(
            message=obj,
            user=user
        ).first()
        return receipt.status == "read" if receipt else False

    def get_reply_to_text(self, obj):
        return obj.reply_to.text if obj.reply_to else None

    def get_reply_to_sender(self, obj):
        if not obj.reply_to:
            return None
        u = obj.reply_to.sender
        if hasattr(u, "student_profile"):
            return u.student_profile.full_name
        if hasattr(u, "teacher_profile"):
            return u.teacher_profile.full_name
        return u.phone

    # ---------------------- NEW METHOD ----------------------

    def get_independent_data(self, obj):
        if not obj.independent:
            return None

        request = self.context.get("request")
        if not request:
            return None

        session_key = f"independent_sent_message_{obj.id}"
        if request.session.get(session_key):
            return None

        try:
            independent_obj = (
                TopicHelpRequestIndependent.objects
                .select_related("subject")
                .prefetch_related("chapters", "topics")
                .get(id=obj.independent)
            )
        except TopicHelpRequestIndependent.DoesNotExist:
            return None

        result_json = independent_obj.result_json or {}

        # 🔥 MUHIM FIX (dict yoki list bo‘lishidan qat’i nazar)
        if isinstance(result_json, dict):
            result_list = result_json.get("result", [])
        elif isinstance(result_json, list):
            result_list = result_json
        else:
            result_list = []

        result = result_list[0] if result_list else {}

        data = {
            "subject": {
                "id": independent_obj.subject.id,
                "class_num": independent_obj.subject.classes.name,
                "name_uz": independent_obj.subject.name_uz,
                "name_ru": independent_obj.subject.name_ru,
            },
            "chapters": [
                {
                    "id": ch.id,
                    "name_uz": ch.name_uz,
                    "name_ru": ch.name_ru,
                }
                for ch in independent_obj.chapters.all()
            ],
            "topics": [
                {
                    "id": tp.id,
                    "name_uz": tp.name_uz,
                    "name_ru": tp.name_ru,
                }
                for tp in independent_obj.topics.all()
            ],
            "result": {
                "score": result.get("score"),
                "total_answers": result.get("total_answers"),
                "correct_answers": result.get("correct_answers"),
            }
        }

        request.session[session_key] = True
        return data







class ConversationListSerializer(ConversationMetaMixin, serializers.ModelSerializer):
    other_user_name = serializers.SerializerMethodField()
    other_user_id = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "chat_type",
            "last_message",
            "last_message_at",
            "is_closed",
            "is_close_requested",
            "close_requested_at",
            "close_requested_by_id",
            "close_requested_by_name",
            "rating",
            "other_user_name",
            "other_user_id",
            "unread_count",
        ]

    def get_unread_count(self, obj):
        user = self.context["request"].user
        participant = obj.participants.filter(user=user).first()
        return participant.unread_count if participant else 0
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
