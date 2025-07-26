from rest_framework.generics import CreateAPIView, ListAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.timezone import now
from django_app.app_student.models import  TopicHelpRequestIndependent
from django_app.app_student.serializers import  TopicHelpRequestIndependentSerializer


from .telegram_bot_service import send_question_to_telegram

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

        # O‘quvchi ni aniqlash
        student = getattr(request.user, 'student_profile', None)
        if student and student.telegram_id and student.telegram_id != 0:
            send_question_to_telegram(student.full_name, instance.id)

        return Response({
            "success": True,
            "message": "O‘qituvchiga yuborildi"
        }, status=status.HTTP_201_CREATED)


