from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from django_app.app_user.models import  Student, StudentLoginHistory
from django_app.app_student.paginations import  StandardResultsSetPagination
from django_app.app_student.serializers  import StudentLoginHistorySerializer

class StudentLoginHistoryListAPIView(ListAPIView):
    serializer_class = StudentLoginHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        try:
            student = Student.objects.get(user=user)
            return StudentLoginHistory.objects.filter(student=student).order_by('-login_time')
        except Student.DoesNotExist:
            return StudentLoginHistory.objects.none()
