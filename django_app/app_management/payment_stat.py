from datetime import timedelta
from django.db.models import Sum, Count
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from .permissions import IsTeacher
from django_app.app_payments.models import Payment, SubscriptionPlan

class PaymentStatisticsAPIView(APIView):
    permission_classes = [IsTeacher] 

    def get(self, request):
        # 🟩 Parametrlar
        years_param = request.query_params.get('years')  # ?years=2024,2025
        if years_param:
            years = [int(y) for y in years_param.split(',') if y.isdigit()]
        else:
            years = [now().year]

        today = now()
        first_day_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        last_day_last_month = today.replace(day=1) - timedelta(days=1)

        payments_success = Payment.objects.filter(status="success")

        # 1. Umumiy tushum
        total_amount = payments_success.aggregate(total=Sum('amount'))['total'] or 0

        # 2. Oxirgi oydagi tushum
        last_month_amount = payments_success.filter(
            payment_date__date__gte=first_day_last_month.date(),
            payment_date__date__lte=last_day_last_month.date()
        ).aggregate(total=Sum('amount'))['total'] or 0

        # 3. Yillik tushumlar (dynamic)
        year_amounts = {}
        for y in years:
            year_sum = payments_success.filter(payment_date__year=y).aggregate(total=Sum('amount'))['total'] or 0
            year_amounts[f"year_{y}"] = year_sum

        # 4. Faol obunachilar soni
        active_subscribers = payments_success.filter(subscription_months__gt=0).values('student').distinct().count()

        # 5. Qaysi SubscriptionPlan eng ko‘p sotilgan
        plan_counts = payments_success.values('subscription_months').annotate(count=Count('id'))
        if plan_counts:
            most_sold_plan_months = max(plan_counts, key=lambda x: x['count'])['subscription_months']
            try:
                most_sold_plan = SubscriptionPlan.objects.get(months=most_sold_plan_months).get_months_display()
            except SubscriptionPlan.DoesNotExist:
                most_sold_plan = f"{most_sold_plan_months} oylik"
        else:
            most_sold_plan = None

        # 6. Har bir rejadan tushgan tushum
        plans_revenue = []
        for plan in SubscriptionPlan.objects.all():
            revenue = payments_success.filter(subscription_months=plan.months).aggregate(total=Sum('amount'))['total'] or 0
            plans_revenue.append({
                'plan': plan.get_months_display(),
                'revenue': revenue,
            })

        # 7. Studentga berilgan umumiy keshbek
        total_student_cashback = payments_success.aggregate(
            total=Sum('student_cashback_amount')
        )['total'] or 0

        # 8. Teacherga berilgan umumiy keshbek
        total_teacher_cashback = payments_success.aggregate(
            total=Sum('teacher_cashback_amount')
        )['total'] or 0

        # 9. Qaysi kupon turi eng ko‘p ishlatilgan
        coupon_type_counts = payments_success.values('coupon_type').annotate(count=Count('id')).order_by('-count')
        top_coupon_type = coupon_type_counts[0]['coupon_type'] if coupon_type_counts else None

        # 10. Har oy qancha yangi obuna
        monthly_subscriptions = payments_success.extra(
            select={'month': "EXTRACT(MONTH FROM payment_date)"}
        ).values('month').annotate(count=Count('id')).order_by('month')
        monthly_data = [{'month': int(item['month']), 'count': item['count']} for item in monthly_subscriptions]

        return Response({
            "total_amount": total_amount,
            "last_month_amount": last_month_amount,
            **year_amounts,  # yil_2025, yil_2024 ...
            "active_subscribers": active_subscribers,
            "most_sold_plan": most_sold_plan,
            "plans_revenue": plans_revenue,
            "total_student_cashback": total_student_cashback,
            "total_teacher_cashback": total_teacher_cashback,
            "top_coupon_type": top_coupon_type,
            "monthly_subscriptions": monthly_data
        })
