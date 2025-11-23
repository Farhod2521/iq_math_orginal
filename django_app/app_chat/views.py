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
        reply_to_id = request.data.get("reply_to")

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

        # Reply qilingan xabarni topamiz (agar bo‘lsa)
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
            reply_to=reply_to   # <<< ASOSIY QISM
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



class TeacherChatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # faqat TEACHER ruxsat 
        if user.role != "teacher":
            return Response({"error": "Faqat o‘qituvchi uchun"}, status=403)

        teacher_user = user

        # o‘qituvchi ishtirok etgan barcha chatlar
        conversations = Conversation.objects.filter(
            participants__user=teacher_user
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

        # chat mavjudmi?
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            return Response({"error": "Chat topilmadi"}, status=404)

        # user shu chatda bormi?
        if not ConversationParticipant.objects.filter(conversation=conversation, user=user).exists():
            return Response({"error": "Siz bu chatda ishtirok etmayapsiz"}, status=403)

        # chatdagi barcha xabarlar
        messages = Message.objects.filter(conversation=conversation).order_by("created_at")

        # 🔥 1. HAR BIR XABARNI 'read' QILIB BELGILAYMIZ
        for msg in messages:
            MessageReceipt.objects.update_or_create(
                message=msg,
                user=user,
                defaults={"status": "read"}
            )

        # 🔥 2. unread_count-ni nol qilamiz (teacher yoki studentga qarab)
        part = ConversationParticipant.objects.get(conversation=conversation, user=user)
        part.unread_count = 0
        part.last_read_at = now()
        part.save()

        # 🔥 3. Xabarlarni serialize qilamiz
        serializer = MessageSerializer(
            messages,
            many=True,
            context={"request": request}
        )

        return Response({
            "conversation_id": conversation.id,
            "messages": serializer.data,
        }, status=200)

