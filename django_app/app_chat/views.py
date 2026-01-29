from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Conversation, ConversationParticipant, Message, MessageReceipt, ConversationRating, ConversationAssignment
from .serializers import (
    ConversationSerializer, MessageSerializer, ConversationListSerializer, 
    TeacherListSerializer, ConversationTransferSerializer,
    ConfirmCloseAndRateSerializer
    
    )
from django_app.app_user.models import Student, Teacher  # sening user struktura
from django.db.models import Count, Avg, Q
from django.utils.timezone import now
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from .permissions import IsTeacher



class ConversationTransferAPIView(APIView):
    permission_classes = [IsAuthenticated, IsTeacher]

    # 🔹 GET — o‘qituvchilar ro‘yxati
    def get(self, request):
        teachers = Teacher.objects.filter(
            status=True
        )

        serializer = TeacherListSerializer(teachers, many=True)
        return Response(serializer.data)

    # 🔹 POST — chatni boshqa o‘qituvchiga o‘tkazish
    def post(self, request):
        serializer = ConversationTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        conversation_id = serializer.validated_data["conversation_id"]
        teacher_id = serializer.validated_data["teacher_id"]
        reason = serializer.validated_data.get("reason", "")

        conversation = get_object_or_404(Conversation, id=conversation_id)
        new_teacher = get_object_or_404(Teacher, id=teacher_id)

        # 🔍 eski teacher (chatda turgani)
        old_teacher = Teacher.objects.filter(
            user__chat_participations__conversation=conversation
        ).first()

        # ❌ eski teacherni chatdan chiqaramiz
        if old_teacher:
            ConversationParticipant.objects.filter(
                conversation=conversation,
                user=old_teacher.user
            ).delete()

        # ✅ yangi teacherni chatga qo‘shamiz
        ConversationParticipant.objects.get_or_create(
            conversation=conversation,
            user=new_teacher.user
        )

        # 🧠 transfer tarixi
        ConversationAssignment.objects.create(
            conversation=conversation,
            from_teacher=old_teacher,
            to_teacher=new_teacher,
            reason=reason,
            assigned_by=request.user
        )

        # 📢 system xabar
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            message_type="system",
            text=f"Chat {new_teacher.full_name} ga o‘tkazildi"
        )

        # 🕒 chat meta update
        conversation.last_message = "Chat boshqa o‘qituvchiga o‘tkazildi"
        conversation.last_message_at = timezone.now()
        conversation.save(update_fields=["last_message", "last_message_at"])

        return Response({
            "success": True,
            "message": "Chat muvaffaqiyatli o‘tkazildi",
            "to_teacher": {
                "id": new_teacher.id,
                "full_name": new_teacher.full_name
            }
        })













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
from django.db.models import Sum
class TotalUnreadChatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        total_unread = (
            user.chat_participations.aggregate(
                total=Sum("unread_count")
            )["total"] or 0
        )

        return Response(
            {
                "total_unread_messages": total_unread
            },
            status=200
        )

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


class RequestCloseConversationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        user = request.user

        conversation = get_object_or_404(Conversation, id=conversation_id)

        if conversation.is_closed:
            return Response(
                {"detail": "Chat allaqachon yopilgan"},
                status=400
            )

        # Faqat teacher
        if user.role != "teacher":
            return Response(
                {"detail": "Faqat o‘qituvchi chatni yopishni so‘rashi mumkin"},
                status=403
            )

        # Chatda ishtirokchimi?
        if not ConversationParticipant.objects.filter(
            conversation=conversation,
            user=user
        ).exists():
            return Response(
                {"detail": "Siz bu chatda ishtirok etmaysiz"},
                status=403
            )

        # Allaqachon so‘ralganmi?
        if conversation.is_close_requested:
            return Response(
                {"detail": "Yopish so‘rovi allaqachon yuborilgan"},
                status=400
            )

        # 🔹 Close request
        conversation.is_close_requested = True
        conversation.close_requested_at = timezone.now()
        conversation.close_requested_by = user
        conversation.save(update_fields=[
            "is_close_requested",
            "close_requested_at",
            "close_requested_by"
        ])

        # 📢 Studentga system xabar
        Message.objects.create(
            conversation=conversation,
            sender=user,
            message_type="system",
            text="O‘qituvchi chatni yopmoqchi. Boshqa savolingiz yo‘qmi?"
        )

        return Response({
            "detail": "Chat yopish so‘rovi studentga yuborildi"
        })


class ConfirmCloseAndRateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        user = request.user

        # 1️⃣ Faqat STUDENT
        if user.role != "student":
            return Response(
                {"detail": "Faqat student tasdiqlab baho bera oladi"},
                status=status.HTTP_403_FORBIDDEN
            )

        conversation = get_object_or_404(Conversation, id=conversation_id)

        # 2️⃣ Chat yopish so‘rovi bo‘lishi shart
        if not conversation.is_close_requested:
            return Response(
                {"detail": "Chat yopish so‘rovi mavjud emas"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3️⃣ Chat allaqachon yopilganmi?
        if conversation.is_closed:
            return Response(
                {"detail": "Chat allaqachon yopilgan"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4️⃣ Student chat ishtirokchisimi?
        if not ConversationParticipant.objects.filter(
            conversation=conversation,
            user=user
        ).exists():
            return Response(
                {"detail": "Siz bu chat ishtirokchisi emassiz"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 5️⃣ Oldin baho berilganmi?
        if hasattr(conversation, "rating"):
            return Response(
                {"detail": "Bu chat allaqachon baholangan"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 6️⃣ Mentor topamiz
        mentor_participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            user__role__in=["teacher", "tutor"]
        ).first()

        if not mentor_participant:
            return Response(
                {"detail": "Mentor topilmadi"},
                status=status.HTTP_400_BAD_REQUEST
            )

        mentor = mentor_participant.user

        serializer = ConfirmCloseAndRateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 🔐 HAMMASI BITTA TRANZAKSIYADA
        with transaction.atomic():

            # 🔒 Chatni yopamiz
            conversation.is_closed = True
            conversation.closed_at = timezone.now()
            conversation.closed_by = conversation.close_requested_by
            conversation.save(update_fields=[
                "is_closed",
                "closed_at",
                "closed_by"
            ])

            # ⭐ Rating
            rating = ConversationRating.objects.create(
                conversation=conversation,
                student=user,
                mentor=mentor,
                stars=serializer.validated_data["stars"],
                comment=serializer.validated_data.get("comment", "")
            )

            # 📢 System xabar
            Message.objects.create(
                conversation=conversation,
                sender=user,
                message_type="system",
                text="Student chatni yopishni tasdiqladi va baho berdi."
            )

        return Response(
            {
                "detail": "Chat yopildi va baho berildi",
                "rating": {
                    "stars": rating.stars,
                    "comment": rating.comment,
                    "mentor_id": mentor.id
                }
            },
            status=status.HTTP_201_CREATED
        )



class TeacherClosedChatsStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Role tekshirish
        if user.role not in ("teacher", "tutor"):
            return Response({"detail": "Foydalanuvchi o'qituvchi emas"}, status=403)

        now = timezone.now()

        # Vaqt chegaralari
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_week = (start_of_day - timezone.timedelta(days=start_of_day.weekday()))
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        # Baza so‘rovlari
        base_filter = Q(closed_by=user, is_closed=True)

        def get_stats(start_date=None):
            filt = base_filter
            if start_date:
                filt &= Q(closed_at__gte=start_date)
            chats = Conversation.objects.filter(filt)

            count = chats.count()

            avg_rating = ConversationRating.objects.filter(
                conversation__in=chats
            ).aggregate(avg=Avg('stars'))['avg']

            return {
                "closed_chats_count": count,
                "average_rating": round(avg_rating, 2) if avg_rating else None
            }

        data = {
            "total": get_stats(),
            "today": get_stats(start_of_day),
            "week": get_stats(start_of_week),
            "month": get_stats(start_of_month),
            "year": get_stats(start_of_year),
        }

        return Response(data, status=200)