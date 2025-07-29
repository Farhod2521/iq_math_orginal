from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone
from datetime import timedelta

from django_app.app_user.models import  Teacher, Student
from django_app.app_teacher.models import TeacherRewardLog
from django_app.app_student.models import   StudentScore
from  django_app.app_payments.models import Subscription
from  django_app.app_teacher.serializers import TeacherRewardSerializer, TeacherRewardLogSerializer
class TeacherRewardAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Auth qilingan userdan teacherni topamiz
        try:
            teacher = request.user.teacher_profile
        except Teacher.DoesNotExist:
            return Response({'detail': 'Siz o‘qituvchi emassiz yoki profil topilmadi.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = TeacherRewardSerializer(data=request.data)
        if serializer.is_valid():
            student_id = serializer.validated_data['student_id']
            reward_type = serializer.validated_data['reward_type']
            amount = serializer.validated_data['amount']
            reason = serializer.validated_data.get('reason', '')

            try:
                student = Student.objects.get(id=student_id)
            except Student.DoesNotExist:
                return Response({'detail': 'O‘quvchi topilmadi'}, status=status.HTTP_404_NOT_FOUND)

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
                    sub_obj.end_date += timedelta(days=amount)
                    sub_obj.save()

            return Response({'detail': 'Rag‘bat muvaffaqiyatli qo‘shildi'}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    



class TeacherRewardListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            teacher = request.user.teacher_profile
        except:
            return Response({'detail': 'Siz o‘qituvchi emassiz.'}, status=status.HTTP_403_FORBIDDEN)

        rewards = TeacherRewardLog.objects.filter(teacher=teacher).order_by('-created_at')
        serializer = TeacherRewardLogSerializer(rewards, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
