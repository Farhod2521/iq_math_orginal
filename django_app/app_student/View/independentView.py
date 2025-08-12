from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now
from django_app.app_student.models import  TopicHelpRequestIndependent
from django_app.app_student.serializers import  TopicHelpRequestIndependentSerializer
from rest_framework.views import APIView
from django.utils import timezone
from .telegram_bot_service import send_question_to_telegram
from django_app.app_teacher.models import Teacher
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

        # Status = sent deb saqlanadi
        instance.status = 'sent'
        instance.save()

        student = getattr(request.user, 'student_profile', None)
        telegram_id = getattr(request.user, 'telegram_id', None)

        if student and telegram_id and telegram_id != 0:
            send_question_to_telegram(
                student_full_name=student.full_name,
                question_id=instance.id,
                result_json=instance.result_json
            )

        return Response({
            "success": True,
            "message": "O‘qituvchiga yuborildi"
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

            # Agar allaqachon biriktirilgan bo‘lsa, boshqa o‘qituvchilarga ruxsat bermaymiz
            if help_request.teacher:
                return Response({
                    "success": False,
                    "message": f"Savolga hozirda {help_request.teacher.full_name} javob beryapti."
                }, status=status.HTTP_403_FORBIDDEN)

            teacher = Teacher.objects.get(telegram_id=telegram_id)

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