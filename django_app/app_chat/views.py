from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Conversation, ConversationParticipant, Message, MessageReceipt, ConversationRating, ConversationAssignment
from .serializers import (
    ConversationSerializer, MessageSerializer, ConversationListSerializer, 
    TeacherListSerializer, ConversationTransferSerializer,
    ConfirmCloseAndRateSerializer, ConversationRatingSerializer
    
    )
from django_app.app_user.models import Student, Teacher  # sening user struktura
from django.db.models import Count, Avg, Q, F, Prefetch, Sum
from django.utils.timezone import now
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from .permissions import IsTeacher
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .services import create_message


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


def get_chat_queryset():
    latest_ratings = ConversationRating.objects.select_related(
        "student",
        "mentor",
    ).order_by("-created_at")

    return (
        Conversation.objects
        .select_related("close_requested_by")
        .prefetch_related(
            "participants__user",
            Prefetch("ratings", queryset=latest_ratings),
        )
    )


def get_chat_queryset_for_user(user):
    return get_chat_queryset().filter(participants__user=user)


def broadcast_chat_message(message, event=None, rating=None):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    payload = {
        "id": message.id,
        "text": message.text,
        "message_type": message.message_type,
        "sender_id": message.sender_id,
        "sender_name": get_user_display_name(message.sender),
        "created_at": message.created_at.isoformat(),
    }
    if event:
        payload["event"] = event
    if rating:
        payload["rating"] = ConversationRatingSerializer(rating).data

    async_to_sync(channel_layer.group_send)(
        f"chat_{message.conversation_id}",
        {
            "type": "chat.message",
            "message": payload,
        },
    )


def create_system_message(conversation, sender, text, event=None, rating=None):
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        message_type="system",
        text=text,
    )

    conversation.last_message = text
    conversation.last_message_at = message.created_at
    conversation.save(update_fields=["last_message", "last_message_at"])

    ConversationParticipant.objects.filter(
        conversation=conversation,
    ).exclude(
        user=sender,
    ).update(unread_count=F("unread_count") + 1)

    transaction.on_commit(
        lambda: broadcast_chat_message(message, event=event, rating=rating)
    )
    return message



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

        # ikkala ishtirokchi o’rtasidagi chatni topamiz (ochiq yoki yopiq)
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


class StudentSupportChatMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        text = request.data.get("text")
        reply_to_id = request.data.get("reply_to")

        if not text and not reply_to_id:
            return Response({"error": "text yoki reply_to yuboring"}, status=400)

        if not hasattr(user, "student_profile"):
            return Response({"error": "Faqat o‘quvchi chat yozishi mumkin"}, status=403)

        student = user.student_profile

        teacher = None
        if student.groups.exists():
            group = student.groups.first()
            teacher = group.teacher
        else:
            teacher = Teacher.objects.filter(support=True).first()

        if not teacher:
            return Response({"error": "Mos o‘qituvchi topilmadi"}, status=400)

        other_user = teacher.user

        conversation = Conversation.objects.filter(
            chat_type="direct",
            participants__user=user
        ).filter(
            participants__user=other_user
        ).first()

        if not conversation:
            conversation = Conversation.objects.create(chat_type="direct")
            ConversationParticipant.objects.bulk_create([
                ConversationParticipant(conversation=conversation, user=user),
                ConversationParticipant(conversation=conversation, user=other_user)
            ])
        elif conversation.is_close_requested:
            conversation.is_close_requested = False
            conversation.close_requested_at = None
            conversation.close_requested_by = None
            conversation.save(update_fields=[
                "is_close_requested", "close_requested_at", "close_requested_by"
            ])
            Message.objects.create(
                conversation=conversation,
                sender=user,
                message_type="system",
                text="Chat qayta ochildi. Yangi savol yozishingiz mumkin."
            )

        try:
            message = create_message(
                conversation_id=conversation.id,
                sender=user,
                text=text,
                reply_to_id=reply_to_id,
            )
        except Exception:
            return Response({"error": "Xabar yuborib bo‘lmadi"}, status=400)

        channel_layer = get_channel_layer()
        if channel_layer:
            sender_name = (
                getattr(user, "full_name", None)
                or getattr(user, "get_full_name", lambda: "")()
                or str(user)
            )
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.id}",
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

        return Response(
            {
                "conversation": ConversationSerializer(conversation).data,
                "message": MessageSerializer(message, context={"request": request}).data,
            },
            status=201,
        )


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

        # Yopish so'rovi bo'lsa va student yozsa — so'rovni bekor qilamiz
        if conversation.is_close_requested and user.role == "student":
            conversation.is_close_requested = False
            conversation.close_requested_at = None
            conversation.close_requested_by = None
            conversation.save(update_fields=[
                "is_close_requested", "close_requested_at", "close_requested_by"
            ])
            Message.objects.create(
                conversation=conversation,
                sender=user,
                message_type="system",
                text="Student yangi savol yozdi. Chat davom etmoqda."
            )

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
        conversation.save(update_fields=["last_message", "last_message_at"])

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
        conversations = get_chat_queryset_for_user(user).order_by("-last_message_at", "-created_at")

        serializer = ConversationListSerializer(
            conversations,
            many=True,
            context={"request": request}
        )

        return Response(serializer.data, status=200)


class LatestConversationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversation = (
            get_chat_queryset_for_user(request.user)
            .order_by("-last_message_at", "-created_at")
            .first()
        )

        if not conversation:
            return Response({"detail": "Chat topilmadi"}, status=404)

        serializer = ConversationListSerializer(
            conversation,
            context={"request": request}
        )
        return Response(serializer.data, status=200)


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
            conversation = get_chat_queryset().get(id=conversation_id)
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
            "conversation": ConversationSerializer(
                conversation,
                context={"request": request}
            ).data,
            "messages": serializer.data,
        }, status=200)


class RequestCloseConversationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        user = request.user

        conversation = get_object_or_404(Conversation, id=conversation_id)

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
        system_message = create_system_message(
            conversation=conversation,
            sender=user,
            text="O'qituvchi chatni yopmoqchi. Boshqa savolingiz yo'qmi?",
            event="close_requested",
        )

        return Response({
            "detail": "Chat yopish so'rovi studentga yuborildi",
            "conversation": ConversationSerializer(
                conversation,
                context={"request": request}
            ).data,
            "message": MessageSerializer(
                system_message,
                context={"request": request}
            ).data,
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

        # 2️⃣ Chat yopish so’rovi bo’lishi shart
        if not conversation.is_close_requested:
            return Response(
                {"detail": "O’qituvchi hali baho so’rovini yubormagan"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3️⃣ Student chat ishtirokchisimi?
        if not ConversationParticipant.objects.filter(
            conversation=conversation,
            user=user
        ).exists():
            return Response(
                {"detail": "Siz bu chat ishtirokchisi emassiz"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 5️⃣ Mentor topamiz
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

        with transaction.atomic():
            # Faqat so'rovni bekor qilamiz — chat YOPILMAYDI
            conversation.is_close_requested = False
            conversation.close_requested_at = None
            conversation.close_requested_by = None
            conversation.save(update_fields=[
                "is_close_requested",
                "close_requested_at",
                "close_requested_by",
            ])

            # ⭐ Rating saqlanadi
            rating = ConversationRating.objects.create(
                conversation=conversation,
                student=user,
                mentor=mentor,
                stars=serializer.validated_data["stars"],
                comment=serializer.validated_data.get("comment", "")
            )

            # 📢 Baxo chat ichida ko'rinadi, chat davom etadi
            system_message = create_system_message(
                conversation=conversation,
                sender=user,
                text=f"Student baho berdi: {'⭐' * serializer.validated_data['stars']}. Chat davom etmoqda.",
                event="rated",
                rating=rating,
            )

        return Response(
            {
                "detail": "Baho berildi. Chat davom etmoqda.",
                "conversation": ConversationSerializer(
                    conversation,
                    context={"request": request}
                ).data,
                "message": MessageSerializer(
                    system_message,
                    context={"request": request}
                ).data,
                "rating": ConversationRatingSerializer(rating).data,
            },
            status=status.HTTP_201_CREATED
        )



class TeacherClosedChatsStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Role tekshirish
        if user.role not in ("teacher"):
            return Response({"detail": "Foydalanuvchi o'qituvchi emas"}, status=403)

        now = timezone.now()

        # Vaqt chegaralari
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_week = (start_of_day - timezone.timedelta(days=start_of_day.weekday()))
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        # Statistika ConversationRating bo’yicha (har bir yopilgan session = 1 rating)
        def get_stats(start_date=None):
            filt = Q(mentor=user)
            if start_date:
                filt &= Q(created_at__gte=start_date)

            ratings = ConversationRating.objects.filter(filt)
            count = ratings.count()
            avg_rating = ratings.aggregate(avg=Avg("stars"))["avg"]

            return {
                "closed_chats_count": count,
                "average_rating": round(avg_rating, 2) if avg_rating else None,
            }

        data = {
            "total": get_stats(),
            "today": get_stats(start_of_day),
            "week": get_stats(start_of_week),
            "month": get_stats(start_of_month),
            "year": get_stats(start_of_year),
        }

        return Response(data, status=200)



class SuperAdminTeachersClosedChatsStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != "superadmin":
            return Response(
                {"detail": "Faqat superadmin uchun"},
                status=403
            )

        now = timezone.now()

        # vaqtlar
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_week = start_of_day - timezone.timedelta(days=start_of_day.weekday())
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        teachers = Teacher.objects.select_related('user').filter(
            user__role="teacher",
            is_verified_teacher=True
        )

        def get_stats(teacher_user, start_date=None):
            filt = Q(mentor=teacher_user)
            if start_date:
                filt &= Q(created_at__gte=start_date)

            ratings = ConversationRating.objects.filter(filt)
            count = ratings.count()
            avg_rating = ratings.aggregate(avg=Avg("stars"))["avg"]

            return {
                "closed_chats_count": count,
                "average_rating": round(avg_rating, 2) if avg_rating else None,
            }

        data = []

        for teacher in teachers:
            data.append({
                "teacher_id": teacher.id,
                "full_name": teacher.full_name,
                "region": teacher.region,
                "total": get_stats(teacher.user),
                "today": get_stats(teacher.user, start_of_day),
                "week": get_stats(teacher.user, start_of_week),
                "month": get_stats(teacher.user, start_of_month),
                "year": get_stats(teacher.user, start_of_year),
            })

        return Response(data, status=200)


class TeacherStatsByIdAPIView(APIView):
    """
    POST { "teacher_id": 5 }
    → shu teacher qancha chatga javob bergan (ConversationRating bo'yicha)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        teacher_id = request.data.get("teacher_id")
        if not teacher_id:
            return Response({"detail": "teacher_id yuborilmadi"}, status=400)

        teacher = get_object_or_404(Teacher, id=teacher_id)
        teacher_user = teacher.user

        now = timezone.now()
        start_of_day   = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_week  = start_of_day - timezone.timedelta(days=start_of_day.weekday())
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_year  = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        def get_stats(start_date=None):
            filt = Q(mentor=teacher_user)
            if start_date:
                filt &= Q(created_at__gte=start_date)
            ratings = ConversationRating.objects.filter(filt)
            count = ratings.count()
            avg_rating = ratings.aggregate(avg=Avg("stars"))["avg"]
            return {
                "closed_chats_count": count,
                "average_rating": round(avg_rating, 2) if avg_rating else None,
            }

        return Response({
            "teacher_id": teacher.id,
            "full_name": teacher.full_name,
            "total":  get_stats(),
            "today":  get_stats(start_of_day),
            "week":   get_stats(start_of_week),
            "month":  get_stats(start_of_month),
            "year":   get_stats(start_of_year),
        }, status=200)
