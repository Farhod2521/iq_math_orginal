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
