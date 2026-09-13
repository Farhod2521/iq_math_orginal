"""
O'qituvchilar (tutorlar) reytingi.

Reyting o'qituvchi promo kodi yoki referal havolasi orqali qabul qilgan
o'quvchilar soni bo'yicha tuziladi. Bir o'quvchi bir marta sanaladi:
referal va kupon orqali ikki marta kelgan bo'lsa ham.
"""

from collections import defaultdict
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_management.models import CouponUsage_Tutor_Student
from django_app.app_user.models import Tutor

from .helpers import IsTutor, get_tutor
from .models import TutorCouponTransaction, TutorGroup, TutorReferralTransaction

ALLOWED_COUNTS = (10, 50, 100, 1000)
ALLOWED_PERIODS = (7, 30, 90, 365)


def _period_start(period):
    """period: 'all' yoki kunlar soni."""
    if period == 'all':
        return None
    return timezone.now() - timedelta(days=period)


def _parse_period(raw):
    raw = (raw or 'all').strip().lower()
    if raw in ('all', '', '0'):
        return 'all'
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 'all'
    return value if value in ALLOWED_PERIODS else 'all'


def _collect_student_sets(period_start):
    """
    {tutor_id: {"referral": set(student_id), "coupon": set(student_id)}}
    Uch manba bo'yicha yig'iladi, har biri uchta so'rov.
    """
    buckets = defaultdict(lambda: {"referral": set(), "coupon": set()})

    referral_qs = TutorReferralTransaction.objects.all()
    coupon_qs = TutorCouponTransaction.objects.all()
    usage_qs = CouponUsage_Tutor_Student.objects.filter(
        used_by_tutor__isnull=False, used_by_student__isnull=False
    )

    if period_start is not None:
        referral_qs = referral_qs.filter(used_at__gte=period_start)
        coupon_qs = coupon_qs.filter(used_at__gte=period_start)
        usage_qs = usage_qs.filter(used_at__gte=period_start)

    for tutor_id, student_id in referral_qs.values_list('tutor_id', 'student_id'):
        buckets[tutor_id]["referral"].add(student_id)

    for tutor_id, student_id in coupon_qs.values_list('tutor_id', 'student_id'):
        buckets[tutor_id]["coupon"].add(student_id)

    for tutor_id, student_id in usage_qs.values_list('used_by_tutor_id', 'used_by_student_id'):
        buckets[tutor_id]["coupon"].add(student_id)

    return buckets


class TutorRatingAPIView(APIView):
    """
    GET /api/v1/tutor/tutor/ratings/?top_count=10&period=all

    period: all | 7 | 30 | 90 | 365 (kun)
    top_count: 10 | 50 | 100 | 1000
    """
    permission_classes = [IsTutor]

    def get(self, request):
        me = get_tutor(request)

        period = _parse_period(request.GET.get('period'))
        try:
            top_count = int(request.GET.get('top_count', 10))
        except (TypeError, ValueError):
            top_count = 10
        if top_count not in ALLOWED_COUNTS:
            top_count = 10

        buckets = _collect_student_sets(_period_start(period))

        groups_map = {
            row['tutor_id']: row['total']
            for row in TutorGroup.objects.values('tutor_id').annotate(total=Count('id'))
        }

        tutor_ids = set(buckets.keys()) | {me.id}
        tutors = {
            tutor.id: tutor
            for tutor in Tutor.objects.filter(id__in=tutor_ids)
        }

        rows = []
        for tutor_id, tutor in tutors.items():
            bucket = buckets.get(tutor_id, {"referral": set(), "coupon": set()})
            referral_ids = bucket["referral"]
            coupon_ids = bucket["coupon"]
            total_ids = referral_ids | coupon_ids

            rows.append({
                "tutor_id": tutor_id,
                "full_name": tutor.full_name,
                "identification": tutor.identification,
                "region": tutor.region,
                "districts": tutor.districts,
                "students_count": len(total_ids),
                "referral_count": len(referral_ids),
                "coupon_count": len(coupon_ids),
                "groups_count": groups_map.get(tutor_id, 0),
                "is_me": tutor_id == me.id,
            })

        # Ko'p o'quvchi qabul qilgan yuqorida; teng bo'lsa ism bo'yicha
        rows.sort(key=lambda row: (-row["students_count"], row["full_name"] or ''))

        ranked = []
        for index, row in enumerate(rows):
            row["rank"] = index + 1
            ranked.append(row)

        my_row = next((row for row in ranked if row["is_me"]), None)

        # O'zidan yuqoridagi bilan farq (motivatsiya uchun)
        if my_row and my_row["rank"] > 1:
            above = ranked[my_row["rank"] - 2]
            my_row = dict(my_row, to_next=max(0, above["students_count"] - my_row["students_count"] + 1))
        elif my_row:
            my_row = dict(my_row, to_next=0)

        return Response({
            "period": period,
            "top_count": top_count,
            "total_tutors": len(ranked),
            "results": ranked[:top_count],
            "me": my_row,
        }, status=status.HTTP_200_OK)
