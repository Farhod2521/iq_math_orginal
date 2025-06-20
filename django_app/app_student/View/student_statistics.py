from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Max
from django_app.app_payments.models import Payment
from django_app.app_student.models import StudentScore,  Diagnost_Student, TopicProgress
from django_app.app_user.models import Student
from django.shortcuts import get_object_or_404


class StudentStatisticsDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        student = get_object_or_404(Student, id=student_id)
        score_data = StudentScore.objects.filter(student=student).first()
        all_payments = Payment.objects.filter(student=student)

        # Payment status counts
        success_payments = all_payments.filter(status='success')
        pending_payments = all_payments.filter(status='pending')
        failed_payments = all_payments.filter(status='failed')

        last_payment = success_payments.order_by('-payment_date').first()
        last_payment_date = last_payment.payment_date.strftime("%d/%m/%Y") if last_payment else None
        last_payment_time = last_payment.payment_date.strftime("%H:%M") if last_payment else None
        last_payment_amount = float(last_payment.amount) if last_payment else 0
        total_paid_amount = success_payments.aggregate(total=Sum('amount'))['total'] or 0

        # === Diagnostic data ===
        diagnostika = []
        student_diagnost_list = Diagnost_Student.objects.filter(student=student)

        for diagnost in student_diagnost_list:
            subject_name = diagnost.subject.name
            chapters_count = diagnost.chapters.count()
            topic_ids = diagnost.topic.values_list('id', flat=True)
            total_topics = len(topic_ids)

            # 80% dan yuqori bajarilganlar
            mastered_count = TopicProgress.objects.filter(
                user=student,
                topic_id__in=topic_ids,
                score__gte=80
            ).count()

            mastery_percent = round((mastered_count / total_topics) * 100, 1) if total_topics else 0

            diagnostika.append({
                "subject_name": subject_name,
                "chapters": chapters_count,
                "topics": total_topics,
                "mastered_topics": mastered_count,
                "mastery_percent": mastery_percent
            })

        # === Response JSON ===
        data = {
            'student_id': student.id,
            'full_name': student.full_name,
            'score': score_data.score if score_data else 0,
            'coin': score_data.coin if score_data else 0,
            'last_payment_date': last_payment_date,
            'last_payment_time': last_payment_time,
            'last_payment_amount': last_payment_amount,
            'payment_status_count': {
                'pending': pending_payments.count(),
                'success': success_payments.count(),
                'failed': failed_payments.count(),
            },
            'total_paid_amount': float(total_paid_amount),
            'student_diagnost': diagnostika
        }

        return Response(data)