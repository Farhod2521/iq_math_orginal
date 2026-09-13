"""O'qituvchi (tutor) modullari uchun umumiy yordamchi funksiyalar."""

from django.db.models import Avg
from rest_framework.permissions import BasePermission

from django_app.app_management.models import CouponUsage_Tutor_Student
from django_app.app_user.models import Student

from .models import TutorCouponTransaction, TutorGroup, TutorReferralTransaction


class IsTutor(BasePermission):
    """Faqat tutor profiliga ega foydalanuvchi (admin/superadmin ham ko'ra oladi)."""

    message = "Foydalanuvchi o'qituvchi emas"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, 'tutor_profile', None) is not None


class IsStudent(BasePermission):
    """Faqat o'quvchi profiliga ega foydalanuvchi."""

    message = "Foydalanuvchi o'quvchi emas"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, 'student_profile', None) is not None


def get_student(request):
    """Request egasining o'quvchi profili yoki None."""
    return getattr(request.user, 'student_profile', None)


def get_tutor(request):
    """Request egasining tutor profili yoki None."""
    return getattr(request.user, 'tutor_profile', None)


def get_tutor_student_ids(tutor):
    """
    Tutor o'z promo havolasi yoki kuponi orqali qo'shgan o'quvchilarning id'lari.

    Uchta manba birlashtiriladi:
      1. TutorReferralTransaction — ro'yxatdan o'tishda referal kod ishlatganlar;
      2. TutorCouponTransaction   — tutor kuponi bilan to'lov qilganlar;
      3. CouponUsage_Tutor_Student — kupon ishlatilgan, lekin to'lov hali yakunlanmaganlar;
      4. Tutor guruhlariga taklif orqali qo'shilganlar.
    """
    referral_ids = TutorReferralTransaction.objects.filter(
        tutor=tutor
    ).values_list('student_id', flat=True)

    coupon_ids = TutorCouponTransaction.objects.filter(
        tutor=tutor
    ).values_list('student_id', flat=True)

    usage_ids = CouponUsage_Tutor_Student.objects.filter(
        used_by_tutor=tutor, used_by_student__isnull=False
    ).values_list('used_by_student_id', flat=True)

    # 4. Taklif orqali guruhga qo'shilganlar (promo/kupon orqali kelmagan bo'lishi mumkin)
    group_member_ids = TutorGroup.objects.filter(tutor=tutor).values_list('students__id', flat=True)

    ids = set(referral_ids) | set(coupon_ids) | set(usage_ids)
    ids.update(student_id for student_id in group_member_ids if student_id)
    return ids


def get_tutor_students(tutor):
    """Tutorga tegishli o'quvchilar queryset'i."""
    return Student.objects.filter(
        id__in=get_tutor_student_ids(tutor)
    ).select_related('user', 'class_name', 'class_name__classes')


def get_group_average_map(group_ids):
    """
    {group_id: o'rtacha ball} — guruhlar ro'yxati uchun bitta so'rovda hisoblanadi.
    Ball TopicProgress.score dan olinadi (0-100).
    """
    from django_app.app_student.models import TopicProgress

    if not group_ids:
        return {}

    rows = (
        TopicProgress.objects.filter(user__tutor_groups__id__in=group_ids)
        .values('user__tutor_groups__id')
        .annotate(average=Avg('score'))
    )
    return {
        row['user__tutor_groups__id']: round(float(row['average'] or 0), 1)
        for row in rows
    }
