from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.pagination import PageNumberPagination
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


class ScoreLogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def _build_qs():
    return StudentScoreLog.objects.select_related(
        'student_score__student__user',
        'question__topic__chapter__subject__classes',
    ).order_by('-awarded_at')


def _serialize_log(log):
    student = log.student_score.student
    q = log.question
    topic   = q.topic   if q else None
    chapter = topic.chapter   if topic else None
    subject = chapter.subject if chapter else None
    cls     = subject.classes if subject else None

    return {
        "id": log.id,
        "student_id": student.id,
        "student_full_name": student.full_name,
        "student_identification": student.identification,

        "subject": {
            "id":      subject.id      if subject else None,
            "name_uz": subject.name_uz if subject else None,
            "name_ru": subject.name_ru if subject else None,
            "class_name": cls.name     if cls     else None,
        },

        "chapter": {
            "id":      chapter.id      if chapter else None,
            "name_uz": chapter.name_uz if chapter else None,
            "name_ru": chapter.name_ru if chapter else None,
        },

        "topic": {
            "id":      topic.id      if topic else None,
            "name_uz": topic.name_uz if topic else None,
            "name_ru": topic.name_ru if topic else None,
        },

        "question": {
            "id":              q.id                if q else None,
            "question_text_uz": q.question_text_uz if q else None,
            "question_text_ru": q.question_text_ru if q else None,
        },

        "award_type":   log.award_type,
        "awarded_coin": log.awarded_coin,
        "awarded_at":   log.awarded_at.strftime("%d/%m/%Y %H:%M"),
    }


class StudentScoreLogAPIView(APIView):
    """
    GET  /student/score-log/                  → barcha loglar (superadmin/admin)
    GET  /student/score-log/?student_id=5     → bitta studentning loglari
    GET  /student/score-log/?award_type=coin  → faqat tanga loglari
    GET  /student/score-log/<pk>/             → bitta log detali
    DELETE /student/score-log/<pk>/           → logni o'chirish (superadmin)

    Pagination: ?page=1&page_size=20 (default 20)
    """

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    def get(self, request, pk=None):
        if pk:
            log = get_object_or_404(_build_qs(), pk=pk)
            return Response(_serialize_log(log))

        qs = _build_qs()

        student_id = request.GET.get('student_id')
        if student_id:
            qs = qs.filter(student_score__student__id=student_id)

        award_type = request.GET.get('award_type')
        if award_type in ('coin', 'score'):
            qs = qs.filter(award_type=award_type)

        date_from = request.GET.get('date_from')
        date_to   = request.GET.get('date_to')
        if date_from:
            qs = qs.filter(awarded_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(awarded_at__date__lte=date_to)

        paginator = ScoreLogPagination()
        page = paginator.paginate_queryset(qs, request)
        data = [_serialize_log(log) for log in page]
        return paginator.get_paginated_response(data)

    def delete(self, request, pk=None):
        if not pk:
            return Response({"detail": "pk talab qilinadi"}, status=400)
        log = get_object_or_404(StudentScoreLog, pk=pk)
        log.delete()
        return Response({"detail": "Log o'chirildi"}, status=204)


class MyScoreLogAPIView(APIView):
    """
    GET /student/my-score-log/                  → o'zining loglari
    GET /student/my-score-log/?award_type=coin
    GET /student/my-score-log/?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD

    Pagination: ?page=1&page_size=20 (default 20)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = getattr(request.user, 'student_profile', None)
        if not student:
            return Response({"detail": "Faqat studentlar uchun."}, status=403)

        qs = _build_qs().filter(student_score__student=student)

        award_type = request.GET.get('award_type')
        if award_type in ('coin', 'score'):
            qs = qs.filter(award_type=award_type)

        date_from = request.GET.get('date_from')
        date_to   = request.GET.get('date_to')
        if date_from:
            qs = qs.filter(awarded_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(awarded_at__date__lte=date_to)

        paginator = ScoreLogPagination()
        page = paginator.paginate_queryset(qs, request)
        data = [_serialize_log(log) for log in page]
        return paginator.get_paginated_response(data)
