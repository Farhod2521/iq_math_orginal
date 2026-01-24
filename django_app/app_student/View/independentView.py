from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now
from django_app.app_student.models import  TopicHelpRequestIndependent
from django_app.app_student.serializers import  TopicHelpRequestIndependentSerializer, MyTopicHelpRequestIndependentSerializer, TopicHelpRequestIndependentDetailSerializer
from rest_framework.views import APIView
from django.utils import timezone
from bot_telegram.helped_bot import send_question_to_telegram
from django_app.app_user.models import Teacher, Student
from urllib.parse import quote
from django.shortcuts import get_object_or_404
from django_app.app_chat.models import (
    Conversation,
    ConversationParticipant,
    Message
)

BOT_USERNAME = "iq_mathbot"

class TopicHelpRequestCreateView(CreateAPIView):
    queryset = TopicHelpRequestIndependent.objects.all()
    serializer_class = TopicHelpRequestIndependentSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def create(self, request, *args, **kwargs):
        user = request.user

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        instance.status = "sent"
        instance.save()

        # ❗ FAQAT STUDENT
        if not hasattr(user, "student_profile"):
            return Response(
                {"error": "Faqat o‘quvchi murojaat yubora oladi"},
                status=403
            )

        student = user.student_profile
        student_user = user

        # ================================
        # 🔑 ASOSIY LOGIKA SHU YERDA
        # ================================

        if student.groups.exists():
            # 1️⃣ STUDENT GROUPDA BOR → O‘SHA GROUP TEACHERI
            group = student.groups.first()   # agar bir nechta bo‘lsa, birinchisi
            teachers = Teacher.objects.filter(id=group.teacher_id)

        else:
            # 2️⃣ YANGI STUDENT → SUPPORT TEACHERLAR
            teachers = Teacher.objects.filter(support=True)

        if not teachers.exists():
            return Response(
                {"error": "Mos o‘qituvchi topilmadi"},
                status=400
            )

        # ================================
        # 🔁 CHAT VA MESSAGE
        # ================================

        for teacher in teachers:
            teacher_user = teacher.user

            conversation = Conversation.objects.filter(
                chat_type="direct",
                participants__user=student_user
            ).filter(
                participants__user=teacher_user
            ).first()

            if not conversation:
                conversation = Conversation.objects.create(chat_type="direct")
                ConversationParticipant.objects.bulk_create([
                    ConversationParticipant(conversation=conversation, user=student_user),
                    ConversationParticipant(conversation=conversation, user=teacher_user),
                ])

            text_message = (
                f"📝 O‘quvchi sizga yangi mavzu bo‘yicha yordam so‘radi.\n"
                f"Murojaat ID: {instance.id}\n"
                f"Mavzu(lar): {', '.join([t.name_uz for t in instance.topics.all()])}\n"
            )

            url_message = (
                f"https://iqmath.uz/dashboard/teacher/"
                f"student-examples/{instance.id}"
                f"?student_name={instance.student.full_name}"
            )

            message = Message.objects.create(
                conversation=conversation,
                sender=student_user,
                text=text_message,
                url=url_message,
                independent=instance.id
            )

            conversation.last_message = text_message
            conversation.last_message_at = message.created_at
            conversation.save()

            for part in conversation.participants.exclude(user=student_user):
                part.unread_count += 1
                part.save()

        return Response({
            "success": True,
            "message": "Murojaat muvaffaqiyatli yuborildi",
            "help_request_id": instance.id
        }, status=201)



class AssignTeacherAPIView(APIView):
    def post(self, request):
        help_request_id = request.data.get("help_request_id")
        telegram_id = request.data.get("telegram_id")

        if not help_request_id or not telegram_id:
            return Response({
                "success": False,
                "message": "help_request_id yoki telegram_id yuborilmadi."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            help_request = TopicHelpRequestIndependent.objects.get(id=help_request_id)

            # Agar allaqachon biriktirilgan bo‘lsa
            if help_request.teacher:
                return Response({
                    "success": False,
                    "message": f"Savolga hozirda {help_request.teacher.full_name} javob beryapti."
                }, status=status.HTTP_403_FORBIDDEN)

            teacher = Teacher.objects.get(user__telegram_id=telegram_id)

            help_request.teacher = teacher
            help_request.status = "reviewing"
            help_request.reviewed_at = timezone.now()
            help_request.save()

            return Response({
                "success": True,
                "teacher_name": teacher.full_name
            }, status=status.HTTP_200_OK)

        except TopicHelpRequestIndependent.DoesNotExist:
            return Response({
                "success": False,
                "message": "Savol topilmadi."
            }, status=status.HTTP_404_NOT_FOUND)

        except Teacher.DoesNotExist:
            return Response({
                "success": False,
                "message": "O‘qituvchi topilmadi."
            }, status=status.HTTP_404_NOT_FOUND)

class GetTelegramIdFromTopicHelpAPIView(APIView):
    def post(self, request, *args, **kwargs):
        topic_help_id = request.data.get("topic_help_id")

        if not topic_help_id:
            return Response({"error": "topic_help_id kiritilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            topic_help = TopicHelpRequestIndependent.objects.select_related("student__user").get(id=topic_help_id)
        except TopicHelpRequestIndependent.DoesNotExist:
            return Response({"error": "TopicHelpRequestIndependent topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        telegram_id = topic_help.student.user.telegram_id
        return Response({"telegram_id": telegram_id}, status=status.HTTP_200_OK)
    

from math import ceil
class StudentTopicHelpRequestListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Studentni topish
        try:
            student = user.student_profile
        except:
            return Response(
                {"error": "Faqat talaba uchun ruxsat berilgan"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Pagination parametrlari
        page = int(request.GET.get('page', 1))  # default 1
        size = int(request.GET.get('size', 10))  # default 10

        queryset = TopicHelpRequestIndependent.objects.filter(
            student=student
        ).order_by('-created_at')

        total_count = queryset.count()
        total_pages = ceil(total_count / size) if size > 0 else 1

        # Boshlanish va tugash indekslari
        start = (page - 1) * size
        end = start + size

        paginated_qs = queryset[start:end]

        # 🔹 Yangi serializer
        serializer = TopicHelpRequestIndependentDetailSerializer(paginated_qs, many=True)

        return Response({
            "page": page,
            "size": size,
            "total": total_count,
            "total_pages": total_pages,
            "results": serializer.data
        }, status=status.HTTP_200_OK)
    






class TopicHelpRequestIndependentDetailAPIView(APIView):
    def get(self, request, pk):
        instance = get_object_or_404(TopicHelpRequestIndependent, pk=pk)
        serializer = TopicHelpRequestIndependentDetailSerializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)