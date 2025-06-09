from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django_app.app_user.models import Teacher, Student
from django_app.app_teacher.models import Group
from django_app.app_teacher.serializers import GroupSerializer, GroupSerializer_DETAIL
from django.shortcuts import get_object_or_404

class GroupListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        teacher = get_object_or_404(Teacher, user=request.user)
        groups = Group.objects.filter(teacher=teacher)
        serializer = GroupSerializer(groups, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class GroupCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        teacher = get_object_or_404(Teacher, user=request.user)
        serializer = GroupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(teacher=teacher)  # teacher ni bu yerda uzatyapmiz
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AddStudentsToGroupAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id, teacher__user=request.user)
        student_ids = request.data.get("student_ids", [])
        students = Student.objects.filter(id__in=student_ids)
        group.students.add(*students)
        return Response({"message": "Talabalar guruhga qo'shildi."}, status=status.HTTP_200_OK)
    
class GroupDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        teacher = get_object_or_404(Teacher, user=request.user)
        group = get_object_or_404(Group, pk=pk, teacher=teacher)
        serializer = GroupSerializer(group)
        return Response(serializer.data)