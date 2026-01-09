from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Conversation, ConversationParticipant, Message, MessageReceipt
from .serializers import ConversationSerializer, MessageSerializer, ConversationListSerializer
from django_app.app_user.models import Student, Teacher  # sening user struktura
from django.db.models import Q
from django.utils.timezone import now

class CreateDirectChatAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if user.role == "student":
            student = user.student_profile
            teacher = student.class_name.teacher_profile
            other_user = teacher.user

        elif user.role == "teacher":
            student_id = request.data.get("student_id")
            try:
                other_user = Student.objects.get(id=student_id).user
            except:
                return Response({"error": "Student topilmadi"}, status=404)
        else:
            return Response({"error": "Faqat student yoki teacher chat ochishi mumkin"}, status=403)

        # direct chat bor-yo‘qligini tekshiramiz
        conversation = Conversation.objects.filter(
            chat_type="direct",
            participants__user=user
        ).filter(
            participants__user=other_user
        ).first()

        if conversation:
            return Response(ConversationSerializer(conversation).data)

        # yangi chat
        conversation = Conversation.objects.create(chat_type="direct")

        ConversationParticipant.objects.bulk_create([
            ConversationParticipant(conversation=conversation, user=user),
            ConversationParticipant(conversation=conversation, user=other_user)
        ])

        return Response(ConversationSerializer(conversation).data, status=201)


class SendMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        user = request.user
        text = request.data.get("text")
        file = request.FILES.get("file")
        reply_to_id = request.data.get("reply_to")

        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except:
            return Response({"error": "Chat topilmadi"}, status=404)

        if not ConversationParticipant.objects.filter(
            conversation=conversation, user=user
        ).exists():
            return Response({"error": "Ruxsat yo'q"}, status=403)

        reply_to = None
        if reply_to_id:
            try:
                reply_to = Message.objects.get(id=reply_to_id)
            except:
                return Response({"error": "Reply qilinadigan xabar topilmadi"}, status=404)

        message = Message.objects.create(
            conversation=conversation,
            sender=user,
            text=text,
            file=file,
            reply_to=reply_to
        )

        # last message update
        conversation.last_message = text or "📎 File"
        conversation.last_message_at = message.created_at
        conversation.save()

        # unread_count update (qarshi tarafga)
        for part in conversation.participants.exclude(user=user):
            part.unread_count += 1
            part.save()

        return Response(
            MessageSerializer(message, context={"request": request}).data,
            status=201
        )




class ReadMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        user = request.user

        try:
            message = Message.objects.get(id=message_id)
        except:
            return Response({"error": "Xabar topilmadi"}, status=404)

        MessageReceipt.objects.update_or_create(
            message=message,
            user=user,
            defaults={"status": "read"}
        )

        part = ConversationParticipant.objects.get(
            conversation=message.conversation,
            user=user
        )
        part.unread_count = 0
        part.last_read_at = message.created_at
        part.save()

        return Response({"status": "read"}, status=200)



class UniversalChatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # student yoki teacher farqi yo‘q — ishtirok etgan chatlar
        conversations = Conversation.objects.filter(
            participants__user=user
        ).order_by("-last_message_at")

        serializer = ConversationListSerializer(
            conversations,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data, status=200)

    

class ConversationMessagesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        user = request.user

        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({"error": "Chat topilmadi"}, status=404)

        if not ConversationParticipant.objects.filter(
            conversation=conversation, user=user
        ).exists():
            return Response({"error": "Siz bu chatda ishtirok etmayapsiz"}, status=403)

        messages = (
            Message.objects
            .filter(conversation=conversation)
            .select_related("sender")
            .order_by("created_at")
        )

        # READ status
        MessageReceipt.objects.filter(
            message__in=messages,
            user=user
        ).update(status="read")

        part = ConversationParticipant.objects.get(
            conversation=conversation,
            user=user
        )
        part.unread_count = 0
        part.last_read_at = now()
        part.save(update_fields=["unread_count", "last_read_at"])

        serializer = MessageSerializer(
            messages,
            many=True,
            context={"request": request}
        )

        return Response({
            "conversation_id": conversation.id,
            "messages": serializer.data,
        }, status=200)



