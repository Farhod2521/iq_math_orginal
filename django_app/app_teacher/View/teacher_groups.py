"""
Teacher guruhlari: yaratish, ro'yxat, tahrirlash, o'chirish va
guruhga o'quvchi qo'shish / chiqarish / boshqa guruhga o'tkazish.

Tutor guruhlaridan farqi: kupon va taklif havolasi yo'q. Teacher hech qaysi
guruhga kiritilmagan istalgan o'quvchini o'z guruhiga qo'sha oladi.
Bir o'quvchi bir vaqtda faqat bitta guruhda bo'ladi.
"""

from django.core.paginator import EmptyPage, Paginator
from django.db.models import Avg, Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_student.models import TopicProgress
from django_app.app_teacher.models import Group
from django_app.app_teacher.serializers import (
    TeacherGroupDetailSerializer,
    TeacherGroupListSerializer,
    TeacherGroupStudentSerializer,
    TeacherGroupWriteSerializer,
)
from django_app.app_user.models import Student, Teacher


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'teacher')


def _get_teacher(request):
    return get_object_or_404(Teacher, user=request.user)


def _students_qs(teacher):
    """O'quvchilar — sinf va teacher guruhi bilan birga (N+1 bo'lmasligi uchun)."""
    return Student.objects.select_related('user', 'class_name', 'class_name__classes').prefetch_related(
        Prefetch('groups', queryset=Group.objects.filter(teacher=teacher))
    )


def _teacher_groups(teacher):
    return Group.objects.filter(teacher=teacher).prefetch_related(
        Prefetch('students', queryset=_students_qs(teacher))
    ).order_by('-created_at')


def _average_map(group_ids):
    """{group_id: o'rtacha ball} — bitta so'rovda (TopicProgress.score, 0-100)."""
    if not group_ids:
        return {}
    rows = (
        TopicProgress.objects.filter(user__groups__id__in=group_ids)
        .values('user__groups__id')
        .annotate(average=Avg('score'))
    )
    return {row['user__groups__id']: round(float(row['average'] or 0), 1) for row in rows}


def _detail_response(teacher, pk, status_code=status.HTTP_200_OK):
    group = get_object_or_404(_teacher_groups(teacher), pk=pk)
    serializer = TeacherGroupDetailSerializer(group, context={'average_map': _average_map([group.id])})
    return Response(serializer.data, status=status_code)


def _student_ids(request):
    student_ids = request.data.get('student_ids')
    if student_ids is None:
        student_id = request.data.get('student_id')
        student_ids = [student_id] if student_id else []
    if not isinstance(student_ids, list):
        student_ids = [student_ids]
    return [sid for sid in student_ids if sid]


class TeacherGroupListCreateAPIView(APIView):
    """
    GET  /api/v1/func_teacher/groups/?search=  - teacher guruhlari ro'yxati
    POST /api/v1/func_teacher/groups/          - guruh yaratish {name}
    """
    permission_classes = [IsTeacher]

    def get(self, request):
        teacher = _get_teacher(request)
        groups = Group.objects.filter(teacher=teacher).prefetch_related('students').order_by('-created_at')

        search = request.GET.get('search')
        if search:
            groups = groups.filter(name__icontains=search)

        groups = list(groups)
        serializer = TeacherGroupListSerializer(
            groups, many=True, context={'average_map': _average_map([g.id for g in groups])}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        teacher = _get_teacher(request)
        serializer = TeacherGroupWriteSerializer(data=request.data, context={'teacher': teacher})
        serializer.is_valid(raise_exception=True)
        group = serializer.save(teacher=teacher)
        return _detail_response(teacher, group.pk, status.HTTP_201_CREATED)


class TeacherGroupDetailAPIView(APIView):
    """
    GET    /api/v1/func_teacher/groups/<pk>/ - guruh detali (o'quvchilari bilan)
    PATCH  /api/v1/func_teacher/groups/<pk>/ - nomini o'zgartirish {name}
    DELETE /api/v1/func_teacher/groups/<pk>/ - o'chirish (o'quvchilar guruhsiz qoladi)
    """
    permission_classes = [IsTeacher]

    def get(self, request, pk):
        return _detail_response(_get_teacher(request), pk)

    def patch(self, request, pk):
        teacher = _get_teacher(request)
        group = get_object_or_404(Group, pk=pk, teacher=teacher)
        serializer = TeacherGroupWriteSerializer(group, data=request.data, partial=True, context={'teacher': teacher})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return _detail_response(teacher, pk)

    put = patch

    def delete(self, request, pk):
        group = get_object_or_404(Group, pk=pk, teacher=_get_teacher(request))
        group.delete()
        return Response({"message": "Guruh o'chirildi"}, status=status.HTTP_200_OK)


class TeacherGroupStudentsAPIView(APIView):
    """
    POST   /api/v1/func_teacher/groups/<pk>/students/ - {student_ids: []} qo'shish / shu guruhga o'tkazish
    DELETE /api/v1/func_teacher/groups/<pk>/students/ - {student_ids: []} guruhdan chiqarish

    Qo'shish mumkin bo'lgan o'quvchilar: guruhsizlar va teacherning boshqa guruhlaridagilar.
    """
    permission_classes = [IsTeacher]

    def post(self, request, pk):
        teacher = _get_teacher(request)
        group = get_object_or_404(Group, pk=pk, teacher=teacher)
        student_ids = _student_ids(request)
        if not student_ids:
            return Response({"error": "student_ids bo'sh"}, status=status.HTTP_400_BAD_REQUEST)

        allowed = Student.objects.filter(id__in=student_ids).filter(
            Q(groups__isnull=True) | Q(groups__teacher=teacher)
        ).distinct()
        allowed_ids = set(allowed.values_list('id', flat=True))
        invalid_ids = [sid for sid in student_ids if sid not in allowed_ids]
        if invalid_ids:
            return Response(
                {"error": f"Bu o'quvchilar boshqa o'qituvchi guruhida: {invalid_ids}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Bir o'quvchi faqat bitta guruhda — teacherning boshqa guruhlaridan chiqaramiz
        for other_group in Group.objects.filter(teacher=teacher, students__id__in=allowed_ids).exclude(pk=group.pk).distinct():
            other_group.students.remove(*allowed_ids)
        group.students.add(*allowed_ids)

        return _detail_response(teacher, pk)

    def delete(self, request, pk):
        teacher = _get_teacher(request)
        group = get_object_or_404(Group, pk=pk, teacher=teacher)
        student_ids = _student_ids(request)
        if not student_ids:
            return Response({"error": "student_ids bo'sh"}, status=status.HTTP_400_BAD_REQUEST)

        group.students.remove(*student_ids)
        return _detail_response(teacher, pk)


class TeacherUngroupedStudentsAPIView(APIView):
    """
    GET /api/v1/func_teacher/groups/students-without-group/?search=&page=1&size=50

    Hech qaysi guruhga kiritilmagan barcha o'quvchilar (sahifalangan).
    search — ism, ID yoki telefon bo'yicha.
    """
    permission_classes = [IsTeacher]

    def get(self, request):
        teacher = _get_teacher(request)
        students = _students_qs(teacher).filter(groups__isnull=True).order_by('-id')

        search = request.GET.get('search', '').strip()
        if search:
            students = students.filter(
                Q(full_name__icontains=search)
                | Q(identification__icontains=search)
                | Q(user__phone__icontains=search)
            )

        page = int(request.GET.get('page', 1) or 1)
        size = min(int(request.GET.get('size', 50) or 50), 200)
        paginator = Paginator(students, size)
        try:
            current_page = paginator.page(page)
            results = TeacherGroupStudentSerializer(current_page.object_list, many=True).data
        except EmptyPage:
            results = []

        return Response({
            "page": page,
            "size": size,
            "total": paginator.count,
            "total_pages": paginator.num_pages,
            "results": results,
        }, status=status.HTTP_200_OK)
