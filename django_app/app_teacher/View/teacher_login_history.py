from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from django_app.app_user.models import  Teacher, TeacherLoginHistory
from django_app.app_student.paginations import  StandardResultsSetPagination
from django_app.app_teacher.serializers  import TeacherLoginHistorySerializer

class TeacherLoginHistoryListAPIView(ListAPIView):
    serializer_class = TeacherLoginHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        try:
            student = Teacher.objects.get(user=user)
            return TeacherLoginHistory.objects.filter(student=student).order_by('-login_time')
        except Teacher.DoesNotExist:
            return TeacherLoginHistory.objects.none()
