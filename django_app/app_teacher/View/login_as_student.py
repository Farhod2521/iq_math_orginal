from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta

from  django_app.app_user.models import Student

class LoginAsStudentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, student_id):
        teacher = request.user
        if teacher.role != 'teacher':
            return Response({"detail": "Sizga ruxsat yo'q."}, status=status.HTTP_403_FORBIDDEN)

        try:
            student = Student.objects.get(id=student_id)
            student_user = student.user

            # Token yaratish
            refresh = RefreshToken.for_user(student_user)
            access_token = refresh.access_token
            access_token.set_exp(lifetime=timedelta(hours=13))
            expires_in = timedelta(hours=13).total_seconds()

            # Token ichiga qo‘shimcha payload
            access_token['student_id'] = student.id
            access_token['impersonated_by'] = teacher.id

            return Response({
                "id": student.id,
                "full_name": student.full_name,
                "phone": student_user.phone,
                "role": student_user.role,
                "status": student.status,
                "access_token": str(access_token),
                "refresh_token": str(refresh),
                "expires_in": expires_in,
            })

        except Student.DoesNotExist:
            return Response({"detail": "Student topilmadi."}, status=status.HTTP_404_NOT_FOUND)
