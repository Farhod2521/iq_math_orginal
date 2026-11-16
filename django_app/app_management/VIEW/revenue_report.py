"""
Pul hisoboti (admin panel > Statistika):
  GET /api/v1/management/statistics/revenue/?from=2026-11-01&to=2026-11-30&group=day

  from, to — sana oralig'i (YYYY-MM-DD, ikkalasi ham kiradi). Berilmasa — joriy oy.
  group    — day | month | year (grafik/jadval qanday guruhlanadi)

Faqat muvaffaqiyatli (status=success) to'lovlar hisoblanadi.
Sana: payment_date, bo'lmasa created_at.
Sof foyda = tushum - o'quvchi keshbeki - o'qituvchi keshbeki.
"""
from datetime import date, datetime, time, timedelta

from django.db.models import Count, DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce, TruncDay, TruncMonth, TruncYear
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_management.permissions import IsTeacherOrSuperAdmin
from django_app.app_payments.models import Payment

TRUNC = {'day': TruncDay, 'month': TruncMonth, 'year': TruncYear}
MAX_DAYS_FOR_DAY_GROUP = 400
ZERO = Value(0, output_field=DecimalField(max_digits=14, decimal_places=2))


def _parse_date(value):
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _num(value):
    return float(value or 0)


class RevenueReportAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    def get(self, request):
        today = timezone.localdate()
        date_from = _parse_date(request.query_params.get('from')) or today.replace(day=1)
        date_to = _parse_date(request.query_params.get('to')) or today
        if date_from > date_to:
            date_from, date_to = date_to, date_from

        group = request.query_params.get('group', 'day')
        if group not in TRUNC:
            group = 'day'
        # Juda uzun oraliqni kunma-kun chiqarmaslik
        if group == 'day' and (date_to - date_from).days > MAX_DAYS_FOR_DAY_GROUP:
            group = 'month'

        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(date_from, time.min), tz)
        end = timezone.make_aware(datetime.combine(date_to + timedelta(days=1), time.min), tz)

        qs = (
            Payment.objects.filter(status='success')
            .annotate(paid_at=Coalesce('payment_date', 'created_at'))
            .filter(paid_at__gte=start, paid_at__lt=end)
        )

        totals = qs.aggregate(
            total=Coalesce(Sum('amount'), ZERO),
            original_total=Coalesce(Sum(Coalesce('original_amount', 'amount')), ZERO),
            student_cb=Coalesce(Sum('student_cashback_amount'), ZERO),
            teacher_cb=Coalesce(Sum('teacher_cashback_amount'), ZERO),
            payments=Count('id'),
            students=Count('student', distinct=True),
        )
        amount = _num(totals['total'])
        cashback = _num(totals['student_cb']) + _num(totals['teacher_cb'])

        series_rows = (
            qs.annotate(period=TRUNC[group]('paid_at', tzinfo=tz))
            .values('period')
            .annotate(
                total=Coalesce(Sum('amount'), ZERO),
                cb=Coalesce(Sum(F('student_cashback_amount') + F('teacher_cashback_amount')), ZERO),
                payments=Count('id'),
            )
            .order_by('period')
        )
        fmt = {'day': '%Y-%m-%d', 'month': '%Y-%m', 'year': '%Y'}[group]
        series = [
            {
                'period': row['period'].strftime(fmt),
                'amount': _num(row['total']),
                'net': _num(row['total']) - _num(row['cb']),
                'count': row['payments'],
            }
            for row in series_rows
            if row['period']
        ]

        by_plan = [
            {
                'plan': row['plan__name_uz'] or '—',
                'months': row['subscription_months'],
                'amount': _num(row['total']),
                'count': row['payments'],
            }
            for row in qs.values('plan__name_uz', 'subscription_months')
            .annotate(total=Coalesce(Sum('amount'), ZERO), payments=Count('id'))
            .order_by('-total')
        ]

        return Response({
            'from': date_from.isoformat(),
            'to': date_to.isoformat(),
            'group': group,
            'total_amount': amount,
            'original_amount': _num(totals['original_total']),
            'discount_amount': max(_num(totals['original_total']) - amount, 0),
            'student_cashback': _num(totals['student_cb']),
            'teacher_cashback': _num(totals['teacher_cb']),
            'net_amount': amount - cashback,
            'payments_count': totals['payments'],
            'students_count': totals['students'],
            'average_check': round(amount / totals['payments']) if totals['payments'] else 0,
            'series': series,
            'by_plan': by_plan,
        })
