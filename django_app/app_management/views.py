from rest_framework.generics import ListAPIView
from .models import SystemSettings, FAQ, Product, Banner, Motivation, Elon, UploadedFile
from .serializers import SystemSettingsSerializer, FAQSerializer, ProductSerializer, BannerSerializer, ElonSerializer
from django_app.app_user.models import User, Teacher, Student, Tutor, Parent
from django_app.app_payments.models import Subscription, Payment, SubscriptionPlan
from rest_framework.views import APIView
from rest_framework.response import Response
from django_app.app_management.permissions import IsTeacher

from datetime import timedelta

from datetime import datetime, timezone
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Sum, Count, Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

class UploadSingleFileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):

        if "file" not in request.FILES:
            return Response({"error": "file yuborilmadi!"}, status=400)

        file_obj = request.FILES["file"]

        # 🔥 10 MB = 10 * 1024 * 1024
        max_size = 10 * 1024 * 1024
        if file_obj.size > max_size:
            return Response(
                {"error": "Fayl hajmi 10 MB dan oshmasligi kerak!"},
                status=400
            )

        uploaded = UploadedFile.objects.create(file=file_obj)

        file_url = request.build_absolute_uri(uploaded.file.url)

        return Response(
            {
                "message": "Fayl muvaffaqiyatli yuklandi!",
                "file_url": file_url
            },
            status=status.HTTP_201_CREATED
        )


class ElonListAPIView(APIView):
    def get(self, request):
        elonlar = Elon.objects.all().order_by('-created_at')
        serializer = ElonSerializer(elonlar, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class MotivationAPIView(APIView):
    """
    Har 3 soatda 2 ta motivatsion so‘zni chiqaruvchi API.
    """

    def get(self, request, *args, **kwargs):
        motivations = Motivation.objects.filter(is_active=True).order_by("created_at")

        if not motivations.exists():
            return Response({"detail": "Motivatsion so‘zlar topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        count = motivations.count()

        # 🕒 Hozirgi vaqt
        now = datetime.now(timezone.utc)
        # Kun boshidan o‘tgan soatlar
        hours_since_midnight = now.hour

        # Har 3 soatda o‘zgaradi
        block_index = hours_since_midnight // 3

        # Har 3 soatda 2 tadan chiqaramiz
        start_index = (block_index * 2) % count
        end_index = (start_index + 2) % count

        if end_index > start_index:
            selected = motivations[start_index:end_index]
        else:
            # ro‘yxat aylanishi uchun
            selected = list(motivations[start_index:]) + list(motivations[:end_index])

        data = [
            {
                "title": m.title,
                "content": m.content,
                "created_at": m.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for m in selected
        ]

        return Response({"motivations": data}, status=status.HTTP_200_OK)

class SystemSettingsListView(ListAPIView):
    queryset = SystemSettings.objects.all()
    serializer_class = SystemSettingsSerializer


class FAQListView(ListAPIView):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer


class BannerListView(ListAPIView):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer

class ProductListView(ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer




class FullStatisticsAPIView(APIView):
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
        total_student_cashback=0
        # total_student_cashback = payments_success.aggregate(
        #     total=Sum('student_cashback_amount')
        # )['total'] or 0

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

        # 🔹 Qo‘shimcha statistika
        total_teachers = Teacher.objects.filter(status=True).count()
        total_students = Student.objects.filter(status=True).count()
        total_parents = Parent.objects.filter(status=True).count()
        total_tutors = Tutor.objects.filter(status=True).count()

        five_days_later = today + timedelta(days=5)

        due_soon_subscriptions = Subscription.objects.filter(
            is_paid=False,
            end_date__lte=five_days_later,
            end_date__gte=today
        ).count()

        total_payments = Payment.objects.count()
        pending_payments = Payment.objects.filter(status='pending').count()
        success_payments = Payment.objects.filter(status='success').count()
        failed_payments = Payment.objects.filter(status='failed').count()

        return Response({
            # 🔹 1–10 statistikalar
            "total_amount": total_amount,
            "last_month_amount": last_month_amount,
            **year_amounts,  # year_2025, year_2024 ...
            "active_subscribers": active_subscribers,
            "most_sold_plan": most_sold_plan,
            "plans_revenue": plans_revenue,
            "total_student_cashback": total_student_cashback,
            "total_teacher_cashback": total_teacher_cashback,
            "top_coupon_type": top_coupon_type,
            "monthly_subscriptions": monthly_data,

            # 🔹 qo‘shimcha statistikalar
            "total_teachers": total_teachers,
            "total_students": total_students,
            "total_parents": total_parents,
            "total_tutors": total_tutors,
            "students_due_within_5_days": due_soon_subscriptions,
            "total_payments": total_payments,
            "pending_payments": pending_payments,
            "successful_payments": success_payments,
            "failed_payments": failed_payments,
        })







