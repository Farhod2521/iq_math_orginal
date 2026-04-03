from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from django.shortcuts import get_object_or_404
from django_app.app_student.models import StudentScoreLog
from django_app.app_user.models import Student


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'role', None) in ['superadmin', 'admin']
        )


class StudentScoreLogAPIView(APIView):
    """
    GET  /student/score-log/                     → barcha loglar (superadmin)
    GET  /student/score-log/?student_id=5        → bitta studentning loglari
    GET  /student/score-log/?award_type=coin     → faqat tanga loglari
    GET  /student/score-log/?award_type=score    → faqat ball loglari
    GET  /student/score-log/<pk>/                → bitta log detali
    DELETE /student/score-log/<pk>/              → bitta logni o'chirish (superadmin)
    """

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    def get(self, request, pk=None):
        if pk:
            log = get_object_or_404(StudentScoreLog, pk=pk)
            return Response(self._serialize(log))

        qs = StudentScoreLog.objects.select_related(
            'student_score__student__user', 'question'
        )

        student_id = request.GET.get('student_id')
        if student_id:
            qs = qs.filter(student_score__student__id=student_id)

        award_type = request.GET.get('award_type')
        if award_type in ('coin', 'score'):
            qs = qs.filter(award_type=award_type)

        date_from = request.GET.get('date_from')  # format: YYYY-MM-DD
        date_to = request.GET.get('date_to')
        if date_from:
            qs = qs.filter(awarded_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(awarded_at__date__lte=date_to)

        data = [self._serialize(log) for log in qs]
        return Response({"count": len(data), "results": data})

    def delete(self, request, pk=None):
        if not pk:
            return Response({"detail": "pk talab qilinadi"}, status=400)
        log = get_object_or_404(StudentScoreLog, pk=pk)
        log.delete()
        return Response({"detail": "Log o'chirildi"}, status=204)

    def _serialize(self, log):
        student = log.student_score.student
        return {
            "id": log.id,
            "student_id": student.id,
            "student_full_name": student.full_name,
            "student_identification": student.identification,
            "question_id": log.question.id,
            "award_type": log.award_type,
            "awarded_coin": log.awarded_coin,
            "awarded_at": log.awarded_at.strftime("%d/%m/%Y %H:%M"),
        }
