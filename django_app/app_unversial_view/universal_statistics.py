from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum

from django_app.app_user.models import Student, Parent, Tutor, ParentStudentRelation
from django_app.app_payments.models import Payment, Subscription
from django_app.app_student.models import (
    StudentScore, Diagnost_Student, TopicProgress,
    StudentReferralTransaction, StudentCouponTransaction,
)
from django_app.app_tutor.models import TutorCouponTransaction, TutorReferralTransaction


# ─────────────────────────────────────────────────────────────
#  Yordamchi funksiyalar
# ─────────────────────────────────────────────────────────────

def _student_data(student):
    """Student uchun to'liq statistika."""
    score_data = StudentScore.objects.filter(student=student).first()
    all_payments = Payment.objects.filter(student=student)
    success_payments = all_payments.filter(status='success')
    pending_payments = all_payments.filter(status='pending')
    failed_payments  = all_payments.filter(status='failed')
    last_payment     = success_payments.order_by('-payment_date').first()
    total_paid       = success_payments.aggregate(total=Sum('amount'))['total'] or 0

    diagnostika = []
    for d in Diagnost_Student.objects.filter(student=student):
        topic_ids     = d.topic.values_list('id', flat=True)
        total_topics  = len(topic_ids)
        mastered      = TopicProgress.objects.filter(
            user=student, topic_id__in=topic_ids, score__gte=80
        ).count()
        diagnostika.append({
            "subject_name_uz":  d.subject.name_uz,
            "subject_name_ru":  d.subject.name_ru,
            "chapters":         d.chapters.count(),
            "topics":           total_topics,
            "mastered_topics":  mastered,
            "mastery_percent":  round((mastered / total_topics) * 100, 1) if total_topics else 0,
        })

    try:
        sub = student.subscription
        is_active = sub.is_paid and sub.end_date >= timezone.now()
    except Subscription.DoesNotExist:
        is_active = False

    referral_students = []
    for tx in StudentReferralTransaction.objects.filter(
        by_student=student
    ).select_related('student').order_by('-used_at'):
        s = tx.student
        referral_students.append({
            "student_id":     s.id,
            "full_name":      s.full_name,
            "identification": s.identification,
            "payment_amount": float(tx.payment_amount),
            "bonus_amount":   float(tx.bonus_amount),
            "joined_at":      tx.used_at.strftime("%d/%m/%Y %H:%M"),
        })

    coupon_students = []
    for tx in StudentCouponTransaction.objects.filter(
        by_student=student
    ).select_related('student', 'coupon').order_by('-used_at'):
        s = tx.student
        coupon_students.append({
            "student_id":       s.id,
            "full_name":        s.full_name,
            "identification":   s.identification,
            "coupon_code":      tx.coupon.code,
            "discount_percent": tx.coupon.discount_percent,
            "payment_amount":   float(tx.payment_amount),
            "cashback_amount":  float(tx.cashback_amount),
            "used_at":          tx.used_at.strftime("%d/%m/%Y %H:%M"),
        })

    return {
        "role":             "student",
        "student_id":       student.id,
        "full_name":        student.full_name,
        "identification":   student.identification,
        "phone":            student.user.phone,
        "region":           student.region,
        "districts":        student.districts,
        "status":           student.status,
        "score":            score_data.score if score_data else 0,
        "coin":             score_data.coin  if score_data else 0,
        "is_active":        is_active,
        "last_payment_date":   last_payment.payment_date.strftime("%d/%m/%Y") if last_payment else None,
        "last_payment_time":   last_payment.payment_date.strftime("%H:%M")    if last_payment else None,
        "last_payment_amount": float(last_payment.amount) if last_payment else 0,
        "total_paid_amount":   float(total_paid),
        "payment_status_count": {
            "pending": pending_payments.count(),
            "success": success_payments.count(),
            "failed":  failed_payments.count(),
        },
        "student_diagnost":       diagnostika,
        "referral_students_count": len(referral_students),
        "referral_students":       referral_students,
        "coupon_students_count":   len(coupon_students),
        "coupon_students":         coupon_students,
    }


def _parent_data(parent):
    """Ota-ona uchun profil + biriktirilgan farzandlar."""
    children_data = []
    for rel in ParentStudentRelation.objects.filter(
        parent=parent, is_confirmed=True
    ).select_related('student'):
        student = rel.student
        score   = StudentScore.objects.filter(student=student).first()
        try:
            sub = student.subscription
            is_active     = sub.is_paid and sub.end_date >= timezone.now()
            sub_end_date  = sub.end_date.strftime("%d/%m/%Y") if sub.end_date else None
            remaining     = max((sub.end_date.date() - timezone.now().date()).days, 0) if sub.end_date else 0
        except Subscription.DoesNotExist:
            is_active    = False
            sub_end_date = None
            remaining    = 0

        children_data.append({
            "student_id":          student.id,
            "full_name":           student.full_name,
            "identification":      student.identification,
            "phone":               student.user.phone,
            "region":              student.region,
            "districts":           student.districts,
            "status":              student.status,
            "class_name":          student.class_name.name_uz if student.class_name else None,
            "score":               score.score if score else 0,
            "coin":                score.coin  if score else 0,
            "is_active":           is_active,
            "subscription_end":    sub_end_date,
            "remaining_days":      remaining,
        })

    return {
        "role":           "parent",
        "parent_id":      parent.id,
        "full_name":      parent.full_name,
        "identification": parent.identification,
        "phone":          parent.user.phone,
        "region":         parent.region,
        "districts":      parent.districts,
        "address":        parent.address,
        "status":         parent.status,
        "registered_at":  parent.parent_date.strftime("%d/%m/%Y") if parent.parent_date else None,
        "children_count": len(children_data),
        "children":       children_data,
    }


def _tutor_data(tutor):
    """Tutor uchun profil + kupon/referal o'quvchilar."""
    coupon_students = []
    for tx in TutorCouponTransaction.objects.filter(
        tutor=tutor
    ).select_related('student', 'coupon').order_by('-used_at'):
        s = tx.student
        coupon_students.append({
            "student_id":       s.id,
            "full_name":        s.full_name,
            "identification":   s.identification,
            "phone":            s.user.phone,
            "coupon_code":      tx.coupon.code,
            "discount_percent": tx.coupon.discount_percent,
            "payment_amount":   float(tx.payment_amount),
            "cashback_amount":  float(tx.cashback_amount),
            "used_at":          tx.used_at.strftime("%d/%m/%Y %H:%M"),
        })

    referral_students = []
    for tx in TutorReferralTransaction.objects.filter(
        tutor=tutor
    ).select_related('student').order_by('-used_at'):
        s = tx.student
        referral_students.append({
            "student_id":     s.id,
            "full_name":      s.full_name,
            "identification": s.identification,
            "phone":          s.user.phone,
            "payment_amount": float(tx.payment_amount),
            "bonus_amount":   float(tx.bonus_amount),
            "joined_at":      tx.used_at.strftime("%d/%m/%Y %H:%M"),
        })

    return {
        "role":           "tutor",
        "tutor_id":       tutor.id,
        "full_name":      tutor.full_name,
        "identification": tutor.identification,
        "phone":          tutor.user.phone,
        "region":         tutor.region,
        "districts":      tutor.districts,
        "address":        tutor.address,
        "status":         tutor.status,
        "registered_at":  tutor.tutor_date.strftime("%d/%m/%Y") if tutor.tutor_date else None,
        "coupon_students_count":   len(coupon_students),
        "coupon_students":         coupon_students,
        "referral_students_count": len(referral_students),
        "referral_students":       referral_students,
    }


# ─────────────────────────────────────────────────────────────
#  Universal Statistics View
# ─────────────────────────────────────────────────────────────

class UniversalStatisticsAPIView(APIView):
    """
    POST /api/v1/universal/statistics/<pk>/
    Body: { "role": "student" | "parent" | "tutor" }

    pk — role bo'yicha tegishli profilning id si:
      student → Student.id
      parent  → Parent.id
      tutor   → Tutor.id
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        role = request.data.get("role", "").strip().lower()

        if role == "student":
            student = get_object_or_404(Student, id=pk)
            return Response(_student_data(student))

        elif role == "parent":
            parent = get_object_or_404(Parent, id=pk)
            return Response(_parent_data(parent))

        elif role == "tutor":
            tutor = get_object_or_404(Tutor, id=pk)
            return Response(_tutor_data(tutor))

        return Response(
            {"error": "role noto'g'ri. 'student', 'parent' yoki 'tutor' bo'lishi kerak."},
            status=status.HTTP_400_BAD_REQUEST,
        )
