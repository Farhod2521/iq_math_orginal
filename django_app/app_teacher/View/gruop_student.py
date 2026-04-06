from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django_app.app_user.models import Teacher, Student
from django_app.app_teacher.models import Group
from django_app.app_teacher.serializers import GroupSerializer, GroupSerializer_DETAIL
from django.shortcuts import get_object_or_404
from django_app.app_user.serializers import StudentSerializer


class IsTeacherOrSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['teacher', 'superadmin', 'admin']


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in ['superadmin', 'admin']


def _is_superadmin(user):
    return getattr(user, 'role', None) in ['superadmin', 'admin']


class GroupListAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    def get(self, request):
        if _is_superadmin(request.user):
            # Superadmin: teacher_id berilsa shu teacherniki, aks holda hammasi
            teacher_id = request.GET.get('teacher_id')
            if teacher_id:
                groups = Group.objects.filter(teacher_id=teacher_id)
            else:
                groups = Group.objects.all()
        else:
            teacher = get_object_or_404(Teacher, user=request.user)
            groups = Group.objects.filter(teacher=teacher)

        serializer = GroupSerializer(groups, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GroupCreateAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    def post(self, request):
        if _is_superadmin(request.user):
            teacher_id = request.data.get('teacher_id')
            teacher = get_object_or_404(Teacher, id=teacher_id)
        else:
            teacher = get_object_or_404(Teacher, user=request.user)

        serializer = GroupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(teacher=teacher)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddStudentsToGroupAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    def get(self, request, pk):
        if _is_superadmin(request.user):
            group = get_object_or_404(Group, pk=pk)
        else:
            teacher = get_object_or_404(Teacher, user=request.user)
            group = get_object_or_404(Group, pk=pk, teacher=teacher)

        serializer = GroupSerializer(group)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk=None, group_id=None):
        gid = pk or group_id
        if _is_superadmin(request.user):
            group = get_object_or_404(Group, id=gid)
        else:
            group = get_object_or_404(Group, id=gid, teacher__user=request.user)

        student_ids = request.data.get("student_ids", [])
        students = Student.objects.filter(id__in=student_ids)
        group.students.add(*students)
        return Response({"message": "Talabalar guruhga qo'shildi."}, status=status.HTTP_200_OK)

    def put(self, request, pk):
        if _is_superadmin(request.user):
            group = get_object_or_404(Group, pk=pk)
        else:
            teacher = get_object_or_404(Teacher, user=request.user)
            group = get_object_or_404(Group, pk=pk, teacher=teacher)

        serializer = GroupSerializer(group, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        if _is_superadmin(request.user):
            group = get_object_or_404(Group, pk=pk)
        else:
            teacher = get_object_or_404(Teacher, user=request.user)
            group = get_object_or_404(Group, pk=pk, teacher=teacher)

        group.delete()
        return Response({"message": "Guruh muvaffaqiyatli o'chirildi."}, status=status.HTTP_200_OK)


class StudentsWithoutGroupAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    def get(self, request):
        students_without_group = Student.objects.filter(groups__isnull=True)
        serializer = StudentSerializer(students_without_group, many=True)
        return Response(serializer.data)


class SuperAdminGroupCRUDAPIView(APIView):
    """
    Superadmin uchun guruh CRUD:

    POST   /superadmin/group/           — guruh yaratish (name + teacher_id + student_ids)
    GET    /superadmin/group/           — barcha guruhlar ro'yxati (?teacher_id=5 filter)
    GET    /superadmin/group/<pk>/      — bitta guruh detali
    PUT    /superadmin/group/<pk>/      — guruhni tahrirlash (name, teacher_id, student_ids)
    DELETE /superadmin/group/<pk>/      — guruhni o'chirish
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk=None):
        if pk:
            group = get_object_or_404(Group, pk=pk)
            return Response(self._serialize(group))

        qs = Group.objects.select_related('teacher').prefetch_related('students')
        teacher_id = request.GET.get('teacher_id')
        if teacher_id:
            qs = qs.filter(teacher_id=teacher_id)

        return Response([self._serialize(g) for g in qs])

    def post(self, request):
        name = request.data.get('name', '').strip()
        teacher_id = request.data.get('teacher_id')
        student_ids = request.data.get('student_ids', [])

        if not name:
            return Response({"detail": "name maydoni talab qilinadi"}, status=400)
        if not teacher_id:
            return Response({"detail": "teacher_id maydoni talab qilinadi"}, status=400)

        teacher = get_object_or_404(Teacher, id=teacher_id)
        group = Group.objects.create(name=name, teacher=teacher)

        if student_ids:
            students = Student.objects.filter(id__in=student_ids)
            group.students.set(students)

        return Response(self._serialize(group), status=201)

    def put(self, request, pk=None):
        if not pk:
            return Response({"detail": "pk talab qilinadi"}, status=400)

        group = get_object_or_404(Group, pk=pk)

        name = request.data.get('name', '').strip()
        teacher_id = request.data.get('teacher_id')
        student_ids = request.data.get('student_ids')

        if name:
            group.name = name
        if teacher_id:
            group.teacher = get_object_or_404(Teacher, id=teacher_id)
        group.save()

        if student_ids is not None:
            students = Student.objects.filter(id__in=student_ids)
            group.students.set(students)

        return Response(self._serialize(group))

    def delete(self, request, pk=None):
        if not pk:
            return Response({"detail": "pk talab qilinadi"}, status=400)
        group = get_object_or_404(Group, pk=pk)
        group.delete()
        return Response({"detail": "Guruh o'chirildi"}, status=204)

    def _serialize(self, group):
        return {
            "id": group.id,
            "name": group.name,
            "teacher_id": group.teacher_id,
            "teacher_name": group.teacher.full_name,
            "students": [
                {"id": s.id, "full_name": s.full_name, "identification": s.identification}
                for s in group.students.all()
            ],
            "student_count": group.students.count(),
            "created_at": group.created_at.strftime("%d/%m/%Y %H:%M"),
        }
