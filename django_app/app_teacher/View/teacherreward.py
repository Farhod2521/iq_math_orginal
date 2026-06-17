from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import BasePermission
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta

from django_app.app_user.models import  Teacher, Student
from django_app.app_teacher.models import TeacherRewardLog
from django_app.app_student.models import   StudentScore
from  django_app.app_payments.models import Subscription
from  django_app.app_teacher.serializers import (
    TeacherRewardSerializer,
    TeacherRewardLogSerializer,
    TeacherRewardLogDetailSerializer,
)


class IsSuperAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "role", None) == "superadmin"
        )


class TeacherRewardAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Auth qilingan userdan teacherni topamiz
        try:
            teacher = request.user.teacher_profile
        except Teacher.DoesNotExist:
            return Response({'detail': "Siz o'qituvchi emassiz yoki profil topilmadi."}, status=status.HTTP_403_FORBIDDEN)

        serializer = TeacherRewardSerializer(data=request.data)
        if serializer.is_valid():
            student_id = serializer.validated_data['student_id']
            reward_type = serializer.validated_data['reward_type']
            amount = serializer.validated_data['amount']
            reason = serializer.validated_data.get('reason', '')

            try:
                student = Student.objects.get(id=student_id)
            except Student.DoesNotExist:
                return Response({'detail': "O'quvchi topilmadi"}, status=status.HTTP_404_NOT_FOUND)

            # Log yozamiz
            TeacherRewardLog.objects.create(
                teacher=teacher,
                student=student,
                reward_type=reward_type,
                amount=amount,
                reason=reason
            )

            # Amalni bajarish
            if reward_type == 'score':
                score_obj, _ = StudentScore.objects.get_or_create(student=student)
                score_obj.score += amount
                score_obj.save()

            elif reward_type == 'coin':
                score_obj, _ = StudentScore.objects.get_or_create(student=student)
                score_obj.coin += amount
                score_obj.save()

            elif reward_type == 'subscription_day':
                sub_obj, created = Subscription.objects.get_or_create(
                    student=student,
                    defaults={
                        'end_date': timezone.now() + timedelta(days=amount),
                        'is_paid': True
                    }
                )
                if not created:
                    now = timezone.now()
                    base = now if sub_obj.end_date < now else sub_obj.end_date
                    sub_obj.end_date = base + timedelta(days=amount)
                    sub_obj.is_paid = True
                    sub_obj.save()

            return Response({'detail': "Rag'bat muvaffaqiyatli qo'shildi"}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    



class TeacherRewardListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            teacher = request.user.teacher_profile
        except:
            return Response({'detail': "Siz o'qituvchi emassiz."}, status=status.HTTP_403_FORBIDDEN)

        rewards = TeacherRewardLog.objects.filter(teacher=teacher).order_by('-created_at')
        serializer = TeacherRewardLogSerializer(rewards, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TeacherRewardLogSuperAdminAPIView(APIView):
    permission_classes = [IsSuperAdminOnly]

    def get(self, request, pk=None):
        if pk is not None:
            reward_log = get_object_or_404(TeacherRewardLog, pk=pk)
            serializer = TeacherRewardLogDetailSerializer(reward_log)
            return Response(serializer.data, status=status.HTTP_200_OK)

        qs = TeacherRewardLog.objects.select_related("teacher__user", "student__user").order_by("-created_at")

        # --- FILTER ---
        teacher_id = request.query_params.get("teacher_id")
        student_id = request.query_params.get("student_id")
        reward_type = request.query_params.get("reward_type")
        date_from   = request.query_params.get("date_from")   # YYYY-MM-DD
        date_to     = request.query_params.get("date_to")     # YYYY-MM-DD

        if teacher_id:
            qs = qs.filter(teacher__id=teacher_id)
        if student_id:
            qs = qs.filter(student__id=student_id)
        if reward_type:
            qs = qs.filter(reward_type=reward_type)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        # --- SEARCH ---
        # ?search=Ali  →  teacher yoki student ismi yoki telefoni bo'yicha
        search = request.query_params.get("search", "").strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(teacher__full_name__icontains=search) |
                Q(teacher__user__phone__icontains=search) |
                Q(student__full_name__icontains=search) |
                Q(student__user__phone__icontains=search)
            )

        # --- PAGINATION ---
        try:
            page      = max(1, int(request.query_params.get("page", 1)))
            page_size = min(200, max(1, int(request.query_params.get("page_size", 20))))
        except ValueError:
            page, page_size = 1, 20

        total  = qs.count()
        offset = (page - 1) * page_size
        qs     = qs[offset: offset + page_size]

        serializer = TeacherRewardLogDetailSerializer(qs, many=True)
        return Response({
            "count":     total,
            "page":      page,
            "page_size": page_size,
            "results":   serializer.data,
        }, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        reward_log = get_object_or_404(TeacherRewardLog, pk=pk)
        reward_log.delete()
        return Response(
            {"message": "Teacher reward log o'chirildi."},
            status=status.HTTP_200_OK,
        )
