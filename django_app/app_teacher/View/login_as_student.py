from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
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


class ChangeStudentPasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, student_id):
        teacher = request.user

        # Faqat teacherlar uchun
        if teacher.role != 'teacher':
            return Response({"detail": "Sizga ruxsat yo'q."}, status=status.HTTP_403_FORBIDDEN)

        new_password = request.data.get("new_password")
        if not new_password:
            return Response({"detail": "Yangi parol yuborilmadi."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.get(id=student_id)
            student_user = student.user

            student_user.set_password(new_password)
            student_user.save()

            # Email mavjud bo‘lsa yuboramiz
            if student_user.email:
                subject = "Parolingiz o‘zgartirildi"
                from_email = None  # `DEFAULT_FROM_EMAIL` ishlatiladi
                to_email = student_user.email

                html_content = render_to_string(
                    'emails/password_changed_by_teacher.html',
                    {
                        'student_name': student.full_name,
                        'teacher_name': teacher.teacher_profile.full_name,
                    }
                )

                email = EmailMultiAlternatives(subject, '', from_email, [to_email])
                email.attach_alternative(html_content, "text/html")
                email.send()

            return Response({"detail": "Parol o‘zgartirildi. (Email yuborildi)"}, status=status.HTTP_200_OK)

        except Student.DoesNotExist:
            return Response({"detail": "O‘quvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)