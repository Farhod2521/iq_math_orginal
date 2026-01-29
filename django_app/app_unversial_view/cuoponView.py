from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
import random
import string
from django.utils import timezone
from datetime import timedelta
from rest_framework.permissions import IsAuthenticated
from django_app.app_management.models import Coupon_Tutor_Student, ReferralAndCouponSettings
from .cuoponSerizalizer import CouponCreateSerializer, CouponSerializer
from django_app.app_tutor.models import TutorCouponTransaction
from django_app.app_teacher.models import TeacherCouponTransaction
from django_app.app_student.models import  StudentCouponTransaction
class UniversalCouponAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # --- Unique kupon generatsiya qilish ---
    def _generate_unique_coupon_code(self, length=6):
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choices(chars, k=length))
            if not Coupon_Tutor_Student.objects.filter(code=code).exists():
                return code

    # --- GET: Foydalanuvchining kuponini qaytaradi ---
    def get(self, request):
        user = request.user
        role = user.role

        if role == 'student':
            coupons = Coupon_Tutor_Student.objects.filter(
                created_by_student=user.student_profile
            )

        elif role == 'tutor':
            coupons = Coupon_Tutor_Student.objects.filter(
                created_by_tutor=user.tutor_profile
            )

        elif role == 'teacher':
            coupons = Coupon_Tutor_Student.objects.filter(
                created_by_teacher=user.teacher_profile
            )

        else:
            raise PermissionDenied("Role uchun ruxsat yo‘q!")

        if not coupons.exists():
            return Response(
                {"message": "Siz hali kupon yaratmagansiz."},
                status=status.HTTP_200_OK
            )

        serializer = CouponSerializer(coupons, many=True)

        return Response({
            "message": "Sizning kuponlaringiz:",
            "coupons": serializer.data
        }, status=status.HTTP_200_OK)
    # --- POST: Yangi kupon yaratish ---
    def post(self, request):
        user = request.user
        role = user.role

        # SETTINGS
        try:
            settings = ReferralAndCouponSettings.objects.latest('updated_at')
        except ReferralAndCouponSettings.DoesNotExist:
            return Response({"error": "ReferralAndCouponSettings topilmadi"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Kupon muddati
        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=settings.coupon_valid_days)

        existing_coupon = None
        creator_data = {}

        # --- STUDENT ---
        if role == 'student':
            student = user.student_profile
            existing_coupon = Coupon_Tutor_Student.objects.filter(
                created_by_student=student
            ).first()
            creator_data = {"created_by_student": student}
            discount_percent = settings.coupon_discount_percent

        # --- TUTOR ---
        elif role == 'tutor':
            tutor = user.tutor_profile
            existing_coupon = Coupon_Tutor_Student.objects.filter(
                created_by_tutor=tutor
            ).first()
            creator_data = {"created_by_tutor": tutor}
            discount_percent = settings.coupon_discount_percent

        # --- TEACHER ---
        elif role == 'teacher':
            teacher = user.teacher_profile
            existing_coupon = Coupon_Tutor_Student.objects.filter(
                created_by_teacher=teacher
            ).first()
            creator_data = {"created_by_teacher": teacher}
            discount_percent = settings.coupon_discount_percent_teacher

        else:
            raise PermissionDenied("Role uchun ruxsat yo‘q!")

        # Agar mavjud bo‘lsa — mavjudini qaytarish
        if existing_coupon:
            return Response({
                "message": "Siz allaqachon kupon yaratgansiz",
                "coupon": CouponSerializer(existing_coupon).data
            }, status=status.HTTP_200_OK)

        # Yangi kupon kodi
        coupon_code = self._generate_unique_coupon_code()

        serializer = CouponCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        coupon = serializer.save(
            code=coupon_code,
            discount_percent=discount_percent,
            valid_from=valid_from,
            valid_until=valid_until,
            is_active=True,
            **creator_data
        )

        return Response({
            "message": "Kupon muvaffaqiyatli yaratildi",
            "coupon": CouponSerializer(coupon).data
        }, status=status.HTTP_201_CREATED)

    # --- DELETE: Kuponni o‘chirish ---
    def delete(self, request):
        user = request.user
        role = user.role

        coupon = None

        # Student kuponi
        if role == 'student':
            coupon = Coupon_Tutor_Student.objects.filter(
                created_by_student=user.student_profile
            ).first()

        # Tutor kuponi
        elif role == 'tutor':
            coupon = Coupon_Tutor_Student.objects.filter(
                created_by_tutor=user.tutor_profile
            ).first()

        # Teacher kuponi
        elif role == 'teacher':
            coupon = Coupon_Tutor_Student.objects.filter(
                created_by_teacher=user.teacher_profile
            ).first()

        else:
            raise PermissionDenied("Role uchun ruxsat yo‘q!")

        if coupon is None:
            return Response(
                {"message": "Sizda o‘chiradigan kupon mavjud emas."},
                status=status.HTTP_404_NOT_FOUND
            )

        coupon.delete()

        return Response(
            {"message": "Kupon muvaffaqiyatli o‘chirildi."},
            status=status.HTTP_200_OK
        )



class UniversalCouponTransactionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role = user.role.lower()  # ✔️ TO‘G‘RI

        result = []

        # 1) TUTOR
        if role == "tutor":
            tutor = user.tutor_profile
            transactions = TutorCouponTransaction.objects.filter(tutor=tutor)

            for t in transactions:
                result.append({
                    "id": t.id,
                    "student": t.student.user.full_name,
                    "owner": tutor.user.full_name,
                    "coupon": t.coupon.code,
                    "payment_amount": t.payment_amount,
                    "cashback_amount": t.cashback_amount,
                    "used_at": t.used_at,
                    "type": "tutor"
                })

        # 2) TEACHER
        elif role == "teacher":
            teacher = user.teacher_profile
            transactions = TeacherCouponTransaction.objects.filter(teacher=teacher)

            for t in transactions:
                result.append({
                    "id": t.id,
                    "student": t.student.user.full_name,
                    "owner": teacher.user.full_name,
                    "coupon": t.coupon.code,
                    "payment_amount": t.payment_amount,
                    "used_at": t.used_at,
                    "type": "teacher"
                })

        # 3) STUDENT
        elif role == "student":
            student = user.student_profile

            tutor_part = TutorCouponTransaction.objects.filter(student=student)
            teacher_part = TeacherCouponTransaction.objects.filter(student=student)
            student_part = StudentCouponTransaction.objects.filter(student=student)

            # tutor
            for t in tutor_part:
                result.append({
                    "id": t.id,
                    "student": student.user.full_name,
                    "owner": t.tutor.user.full_name,
                    "coupon": t.coupon.code,
                    "payment_amount": t.payment_amount,
                    "cashback_amount": t.cashback_amount,
                    "used_at": t.used_at,
                    "type": "tutor"
                })

            # teacher
            for t in teacher_part:
                result.append({
                    "id": t.id,
                    "student": student.user.full_name,
                    "owner": t.teacher.user.full_name,
                    "coupon": t.coupon.code,
                    "payment_amount": t.payment_amount,
                    "used_at": t.used_at,
                    "type": "teacher"
                })

            # student → student
            for t in student_part:
                result.append({
                    "id": t.id,
                    "student": student.user.full_name,
                    "owner": t.by_student.user.full_name,
                    "coupon": t.coupon.code,
                    "payment_amount": t.payment_amount,
                    "cashback_amount": t.cashback_amount,
                    "used_at": t.used_at,
                    "type": "student"
                })

        # 4) ADMIN → hammasi
        elif role == "admin":
            for t in TutorCouponTransaction.objects.all():
                result.append({
                    "id": t.id,
                    "student": t.student.user.full_name,
                    "owner": t.tutor.user.full_name,
                    "coupon": t.coupon.code,
                    "payment_amount": t.payment_amount,
                    "cashback_amount": t.cashback_amount,
                    "used_at": t.used_at,
                    "type": "tutor"
                })

            for t in TeacherCouponTransaction.objects.all():
                result.append({
                    "id": t.id,
                    "student": t.student.user.full_name,
                    "owner": t.teacher.user.full_name,
                    "coupon": t.coupon.code,
                    "payment_amount": t.payment_amount,
                    "used_at": t.used_at,
                    "type": "teacher"
                })

            for t in StudentCouponTransaction.objects.all():
                result.append({
                    "id": t.id,
                    "student": t.student.user.full_name,
                    "owner": t.by_student.user.full_name,
                    "coupon": t.coupon.code,
                    "payment_amount": t.payment_amount,
                    "cashback_amount": t.cashback_amount,
                    "used_at": t.used_at,
                    "type": "student"
                })

        else:
            return Response({"error": "Rol aniqlanmadi"}, status=403)

        # Sort by date desc
        result = sorted(result, key=lambda x: x["used_at"], reverse=True)

        return Response(result, status=200)
