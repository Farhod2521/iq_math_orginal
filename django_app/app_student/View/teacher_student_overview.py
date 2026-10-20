"""
O'qituvchi / admin uchun o'quvchi sahifasi (o'quvchi kabineti ko'rinishida).

GET /api/v1/func_student/teacher/students/<student_id>/overview/

Ota-ona "farzand sahifasi" bilan bir xil ma'lumot (build_child_overview) + o'quvchining
bosh sahifasidagi yuqori panel (ketma-ket kunlar, tanga, ball, kundalik maqsad),
telefon va to'lovlar holati bo'yicha sonlar.
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_student.View.parent_dashboard import build_child_overview
from django_app.app_student.View.student_home_dashboard import _header
from django_app.app_user.models import Student, Subject

ALLOWED_ROLES = ("teacher", "admin", "superadmin")


class TeacherStudentOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        from django.db.models import Count, Q

        from django_app.app_payments.models import Payment

        if request.user.role not in ALLOWED_ROLES:
            return Response({"detail": "Ruxsat yo'q."}, status=status.HTTP_403_FORBIDDEN)

        student = (
            Student.objects.filter(id=student_id)
            .select_related("user", "class_name__classes")
            .first()
        )
        if student is None:
            return Response({"detail": "O'quvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        data = build_child_overview(student, request)
        data["header"] = _header(student)
        data["profile"]["phone"] = None if str(student.user.phone or "").startswith("c") else student.user.phone
        data["profile"]["user_id"] = student.user_id
        # Fan kartalari uchun rasm (bazada bo'lsa)
        images = {
            s.id: s.image_uz.url
            for s in Subject.objects.filter(id__in=[row["id"] for row in data["subjects"]]).only("id", "image_uz")
            if s.image_uz
        }
        for row in data["subjects"]:
            row["image"] = images.get(row["id"])
        data["payment_status_count"] = Payment.objects.filter(student=student).aggregate(
            pending=Count("id", filter=Q(status="pending")),
            success=Count("id", filter=Q(status="success")),
            failed=Count("id", filter=Q(status="failed")),
        )
        return Response(data)
