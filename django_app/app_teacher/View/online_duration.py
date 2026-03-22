from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django_app.app_user.models import Teacher, TeacherLoginHistory


class TeacherOnlineDurationAPIView(APIView):
    """
    URL: /teacher/online-duration/<int:teacher_id>/
    teacher_id berilsa — shu o'qituvchining online vaqti ko'rsatiladi.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, teacher_id):
        try:
            teacher = Teacher.objects.get(id=teacher_id)
        except Teacher.DoesNotExist:
            return Response({"detail": "Teacher topilmadi."}, status=404)

        histories = TeacherLoginHistory.objects.filter(teacher=teacher)

        total_seconds = 0
        for h in histories:
            end = h.logout_time if h.logout_time else timezone.now()
            duration = (end - h.login_time).total_seconds()
            if duration > 0:
                total_seconds += duration

        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)

        active_session = histories.filter(logout_time__isnull=True).order_by('-login_time').first()
        current_session_seconds = 0
        if active_session:
            current_session_seconds = int((timezone.now() - active_session.login_time).total_seconds())

        return Response({
            "teacher_id": teacher.id,
            "teacher": teacher.full_name,
            "total_online_seconds": int(total_seconds),
            "total_online_formatted": f"{hours} soat {minutes} daqiqa {seconds} soniya",
            "is_currently_online": active_session is not None,
            "current_session_seconds": current_session_seconds,
            "current_session_formatted": (
                f"{current_session_seconds // 3600} soat "
                f"{(current_session_seconds % 3600) // 60} daqiqa "
                f"{current_session_seconds % 60} soniya"
                if active_session else None
            ),
            "total_sessions": histories.count(),
        })
