from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Conversation, ConversationParticipant, Message, MessageReceipt
from .serializers import ConversationSerializer, MessageSerializer
from django_app.app_user.models import Student, Teacher  # sening user struktura
from django.db.models import Q


class CreateDirectChatAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # Student → Teacher permission
        if user.role == "student":
            student = user.student_profile
            teacher = student.class_name.teacher_profile  # sening strukturangga mos
            other_user = teacher.user

        elif user.role == "teacher":
            teacher = user.teacher_profile
            # Agar teacher student bilan yozsa — student id kelishi kerak
            student_id = request.data.get("student_id")
            try:
                other_user = Student.objects.get(id=student_id).user
            except:
                return Response({"error": "Student topilmadi"}, status=404)
        else:
            return Response({"error": "Faqat student/teacher chat ochishi mumkin"}, status=403)
        

        # OLDIN CHAT BORMI?
        conversation = Conversation.objects.filter(
            chat_type="direct",
            participants__user=user
        ).filter(
            participants__user=other_user
        ).first()

        if conversation:
            return Response(ConversationSerializer(conversation).data)

        # YANGI CHAT
        conversation = Conversation.objects.create(
            chat_type="direct"
        )

        ConversationParticipant.objects.bulk_create([
            ConversationParticipant(conversation=conversation, user=user),
            ConversationParticipant(conversation=conversation, user=other_user),
        ])

        return Response(ConversationSerializer(conversation).data, status=201)


class SendMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        user = request.user
        text = request.data.get("text")
        file = request.FILES.get("file")

        # Chatni chaqiramiz
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except:
            return Response({"error": "Chat topilmadi"}, status=404)

        # User chatda ishtirokchimi?
        if not ConversationParticipant.objects.filter(
            conversation=conversation, user=user
        ).exists():
            return Response({"error": "Ruxsat yo'q"}, status=403)

        message = Message.objects.create(
            conversation=conversation,
            sender=user,
            text=text,
            file=file
        )

        # Conversationni yangilaymiz
        conversation.last_message = text or "📎 File"
        conversation.last_message_at = message.created_at
        conversation.save()

        # Unread count yangilash
        for part in conversation.participants.exclude(user=user):
            part.unread_count += 1
            part.save()

        return Response(MessageSerializer(message).data, status=201)



class ReadMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, message_id):
        user = request.user

        try:
            message = Message.objects.get(id=message_id)
        except:
            return Response({"error": "Xabar topilmadi"}, status=404)

        # Receipt create/update
        MessageReceipt.objects.update_or_create(
            message=message,
            user=user,
            defaults={"status": "read"}
        )

        # unread_countni nol qilish
        part = ConversationParticipant.objects.get(
            conversation=message.conversation,
            user=user
        )
        part.unread_count = 0
        part.last_read_at = message.created_at
        part.save()

        return Response({"status": "read"}, status=200)
