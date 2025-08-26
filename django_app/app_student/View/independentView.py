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
from django_app.app_user.models import Teacher, Student

# views.py
import requests
import urllib.parse
import json
from django_app.app_student.models import HelpRequestMessageLog

BOT_TOKEN = '7826335243:AAGXTZvtzJ8e8g35Hrx_Swy7mwmRPd3T7Po'
TEACHER_CHAT_IDS = [1858379541, 5467533504]  # O'qituvchilarning chat ID lari

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
            self.send_question_to_telegram(
                student_full_name=student.full_name,
                question_id=instance.id,
                result_json=instance.result_json
            )

        return Response({
            "success": True,
            "message": "O'qituvchiga yuborildi"
        }, status=status.HTTP_201_CREATED)

    def send_question_to_telegram(self, student_full_name, question_id, result_json):
        student_name_encoded = urllib.parse.quote(student_full_name)
        url = f"https://mentor.iqmath.uz/dashboard/teacher/student-examples/{question_id}?student_name={student_name_encoded}"

        result = result_json[0] if result_json else {}
        total = result.get("total_answers", "-")
        correct = result.get("correct_answers", "-")
        score = result.get("score", "-")

        text = (
            f"📥 <b>Yangi savol!</b>\n"
            f"👤 <b>O'quvchi:</b> {student_full_name}\n"
            f"🆔 <b>Savol ID:</b> {question_id}\n\n"
            f"📊 <b>Natija:</b>\n"
            f"➕ To'g'ri: <b>{correct}</b> / {total}\n"
            f"⭐️ Ball: <b>{score}</b>\n\n"
        )

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Javob berish", "callback_data": f"assign_{question_id}"},
                ],
                [
                    {"text": "🔗 Savolga o'tish", "url": url}
                ]
            ]
        }

        # Har bir o'qituvchiga yuboramiz
        for chat_id in TEACHER_CHAT_IDS:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": json.dumps(keyboard),
                "disable_web_page_preview": True
            }

            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                data=payload
            )

            if response.ok:
                res_data = response.json()
                message_id = res_data["result"]["message_id"]

                # Bazaga log yozish
                HelpRequestMessageLog.objects.create(
                    help_request_id=question_id,
                    chat_id=chat_id,
                    message_id=message_id
                )


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
        

class GetTelegramIdAPIView(APIView):
    def post(self, request, *args, **kwargs):
        student_id = request.data.get("student_id")

        if not student_id:
            return Response({"error": "student_id kiritilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        # Studentni topish (agar identification ishlatmoqchi bo'lsangiz, filterni shunga qarab o'zgartiring)
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"error": "Student topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        telegram_id = student.user.telegram_id
        return Response({"telegram_id": telegram_id}, status=status.HTTP_200_OK)