from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now
from django_app.app_student.models import  TopicHelpRequestIndependent
from django_app.app_student.serializers import  TopicHelpRequestIndependentSerializer, MyTopicHelpRequestIndependentSerializer
from rest_framework.views import APIView
from django.utils import timezone
from bot_telegram.helped_bot import send_question_to_telegram
from django_app.app_user.models import Teacher, Student, Subject
from urllib.parse import quote
from django_app.app_teacher.models import  Chapter, Topic
BOT_USERNAME = "iq_mathbot"

from urllib.parse import quote
import json

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

        # Request.data dan ma'lumotlarni olish (agar frontend dan kelayotgan bo'lsa)
        info_data = request.data.get('info', {})
        
        subject_id = info_data.get('subject', {}).get('id')
        chapter_id = info_data.get('chapter', {}).get('id')
        topic_id = info_data.get('topic', {}).get('id')
        
        # Modellardan nomlarni olish
        subject_name_uz = ""
        chapter_name_uz = ""
        topic_name_uz = ""
        
        try:
            if subject_id:
                subject = Subject.objects.get(id=subject_id)
                subject_name_uz = getattr(subject, 'name_uz', '')
        except Subject.DoesNotExist:
            subject_name_uz = ""
        
        try:
            if chapter_id:
                chapter = Chapter.objects.get(id=chapter_id)
                chapter_name_uz = getattr(chapter, 'name_uz', '')
        except Chapter.DoesNotExist:
            chapter_name_uz = ""
        
        try:
            if topic_id:
                topic = Topic.objects.get(id=topic_id)
                topic_name_uz = getattr(topic, 'name_uz', '')
        except Topic.DoesNotExist:
            topic_name_uz = ""

        # Result ma'lumotlarini olish
        result_data = instance.result_json or []
        total_answers = 0
        correct_answers = 0
        score = 0
        
        if result_data and len(result_data) > 0:
            result = result_data[0]
            total_answers = result.get('total_answers', 0)
            correct_answers = result.get('correct_answers', 0)
            score = result.get('score', 0)

        # Deep link payload yaratamiz
        payload_data = {
            'instance_id': instance.id,
            'student_id': student.id if student else None,
            'subject_name_uz': subject_name_uz,
            'chapter_name_uz': chapter_name_uz,
            'topic_name_uz': topic_name_uz,
            'total_answers': total_answers,
            'correct_answers': correct_answers,
            'score': score
        }
        
        payload_encoded = quote(json.dumps(payload_data, ensure_ascii=False))
        deep_link = f"https://t.me/{BOT_USERNAME}?start={payload_encoded}"

        # Telegramga xabar yuborish
        if student and telegram_id and telegram_id != 0:
            send_question_to_telegram(
                student_id=student.id,
                student_full_name=student.full_name,
                question_id=instance.id,
                result_json=instance.result_json
            )

        return Response({
            "success": True,
            "message": "O'qituvchiga yuborildi",
            "telegram_link": deep_link,
            "subject_name_uz": subject_name_uz,
            "chapter_name_uz": chapter_name_uz,
            "topic_name_uz": topic_name_uz,
            "result": {
                "total_answers": total_answers,
                "correct_answers": correct_answers,
                "score": score
            }
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