from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Max
from django_app.app_payments.models import Payment
from django_app.app_student.models import StudentScore
from django_app.app_user.models import Student
from django.shortcuts import get_object_or_404


class StudentStatisticsDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        student = get_object_or_404(Student, id=student_id)

        score_data = StudentScore.objects.filter(student=student).first()
        payments = Payment.objects.filter(student=student, status="success")

        total_paid_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
        payment_count = payments.count()
        last_payment_date = payments.aggregate(last=Max('payment_date'))['last']

        data = {
            'student_id': student.id,
            'full_name': student.full_name,
            'score': score_data.score if score_data else 0,
            'coin': score_data.coin if score_data else 0,
            'last_payment_date': last_payment_date,
            'payment_count': payment_count,
            'total_paid_amount': total_paid_amount,
        }

        return Response(data)