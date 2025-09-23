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


BOT_USERNAME = "iq_mathbot"
class TopicHelpRequestCreateView(CreateAPIView):
    queryset = TopicHelpRequestIndependent.objects.all()
    serializer_class = TopicHelpRequestIndependentSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        instance.status = 'sent'
        instance.save()

        student = getattr(request.user, 'student_profile', None)
        telegram_id = getattr(request.user, 'telegram_id', None)

        # deep link payload yaratamiz
        payload = f"{instance.id}_{student.id}"
        payload_encoded = quote(payload)
        deep_link = f"https://t.me/{BOT_USERNAME}?start={payload_encoded}"

        # 🔥 BU QISMI OLIB TASHLASH - O'QITUVCHIGA AVTOMATIK YUBORILMASIN
        # if student and telegram_id and telegram_id != 0:
        #     send_question_to_telegram(
        #         student_id=student.id,
        #         student_full_name=student.full_name,
        #         question_id=instance.id,
        #     )

        return Response({
            "success": True,
            "message": "Murojaat yaratildi. Telegram orqali yuborishingiz mumkin.",
            "telegram_link": deep_link  # frontendga qaytadi
        }, status=status.HTTP_201_CREATED)


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
        total_pages = ceil(total_count / size)

        # Boshlanish va tugash indekslari
        start = (page - 1) * size
        end = start + size

        paginated_qs = queryset[start:end]

        serializer = MyTopicHelpRequestIndependentSerializer(paginated_qs, many=True)

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