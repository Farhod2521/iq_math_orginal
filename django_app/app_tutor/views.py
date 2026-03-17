from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, permissions, status
from django.utils import timezone
from datetime import timedelta
from django_app.app_management.models import Coupon_Tutor_Student, ReferralAndCouponSettings, Referral_Tutor_Student
from django_app.app_user.models import Tutor
from .serializers import (
    CouponCreateSerializer, ReferralCreateSerializer, 
      TutorCouponTransactionSerializer, TutorReferralTransactionSerializer,
      CouponSerializer, ReferralSerializer, TutorWithdrawalSerializer)
from django.db import IntegrityError
from rest_framework.exceptions import PermissionDenied
from .models import TutorCouponTransaction, TutorReferralTransaction, TutorWithdrawal, WithdrawalLimitSettings
import random
import string
from django.db.models import Sum

class TutorCouponViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CouponSerializer

    def get_queryset(self):
        tutor = getattr(self.request.user, 'tutor_profile', None)
        if tutor is None:
            raise PermissionDenied("Foydalanuvchi o‘qituvchi emas")
        return Coupon_Tutor_Student.objects.filter(created_by_tutor=tutor)

    def _generate_unique_coupon_code(self, length=6):
        """A-Z va 0-9 dan iborat unikal kupon kodi yaratish."""
        chars = string.ascii_uppercase + string.digits  # A-Z + 0-9
        while True:
            code = ''.join(random.choices(chars, k=length))
            if not Coupon_Tutor_Student.objects.filter(code=code).exists():
                return code

    def create(self, request, *args, **kwargs):
        try:
            settings = ReferralAndCouponSettings.objects.latest('updated_at')
        except ReferralAndCouponSettings.DoesNotExist:
            return Response({"error": "ReferralAndCouponSettings topilmadi"},
                            status=status.HTTP_400_BAD_REQUEST)

        tutor = getattr(request.user, 'tutor_profile', None)
        if tutor is None:
            raise PermissionDenied("Foydalanuvchi o‘qituvchi emas")

        # 🔹 Agar tutor allaqachon kupon yaratgan bo‘lsa — shuni qaytaramiz
        existing_coupon = Coupon_Tutor_Student.objects.filter(created_by_tutor=tutor).first()
        if existing_coupon:
            return Response({
                "message": "Siz allaqachon kupon yaratgansiz",
                "coupon": CouponSerializer(existing_coupon).data
            }, status=status.HTTP_200_OK)

        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=settings.coupon_valid_days)

        coupon_code = self._generate_unique_coupon_code()

        serializer = CouponCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        coupon = serializer.save(
            code=coupon_code,
            discount_percent=settings.coupon_discount_percent,
            valid_from=valid_from,
            valid_until=valid_until,
            created_by_tutor=tutor,
            is_active=True
        )

        return Response(CouponSerializer(coupon).data, status=status.HTTP_201_CREATED)



class TutorReferralViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReferralSerializer

    def get_queryset(self):
        tutor = getattr(self.request.user, 'tutor_profile', None)
        if tutor is None:
            raise PermissionDenied("Foydalanuvchi o‘qituvchi emas")
        return Referral_Tutor_Student.objects.filter(created_by_tutor=tutor)

    def _generate_unique_referral_code(self, length=6):
        """A-Z va 0-9 dan iborat unikal referal kodi yaratish."""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choices(chars, k=length))
            if not Referral_Tutor_Student.objects.filter(code=code).exists():
                return code

    def create(self, request, *args, **kwargs):
        try:
            settings = ReferralAndCouponSettings.objects.latest('updated_at')
        except ReferralAndCouponSettings.DoesNotExist:
            return Response({"error": "ReferralAndCouponSettings topilmadi"},
                            status=status.HTTP_400_BAD_REQUEST)

        tutor = getattr(request.user, 'tutor_profile', None)
        if tutor is None:
            raise PermissionDenied("Foydalanuvchi o‘qituvchi emas")

        # 🔹 Agar tutor allaqachon referal yaratgan bo‘lsa — shuni qaytaramiz
        existing_referral = Referral_Tutor_Student.objects.filter(created_by_tutor=tutor).first()
        if existing_referral:
            return Response({
                "message": "Siz allaqachon referal link yaratgansiz",
                "referral": ReferralSerializer(existing_referral).data
            }, status=status.HTTP_200_OK)

        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=settings.referral_valid_days)

        referral_code = self._generate_unique_referral_code()

        serializer = ReferralCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        referral = serializer.save(
            code=referral_code,
            bonus_percent=settings.referral_bonus_coin,
            valid_from=valid_from,
            valid_until=valid_until,
            created_by_tutor=tutor,
            is_active=True
        )

        return Response(ReferralSerializer(referral).data, status=status.HTTP_201_CREATED)




class TutorCouponTransactionListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        tutor = getattr(request.user, 'tutor_profile', None)
        if tutor is None:
            return Response({"error": "Foydalanuvchi O‘qituvchi emas"}, status=status.HTTP_403_FORBIDDEN)

        transactions = TutorCouponTransaction.objects.filter(tutor=tutor).select_related('student', 'coupon')
        serializer = TutorCouponTransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TutorReferralTransactionListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        tutor = getattr(request.user, 'tutor_profile', None)
        if tutor is None:
            return Response({"error": "Foydalanuvchi o‘qituvchi emas"}, status=status.HTTP_403_FORBIDDEN)

        # ✅ To‘g‘rilangan select_related
        transactions = TutorReferralTransaction.objects.filter(
            tutor=tutor
        ).select_related('student', 'tutor')

        serializer = TutorReferralTransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    



class TutorEarningsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tutor = getattr(request.user, 'tutor_profile', None)
        if tutor is None:
            return Response({"error": "Foydalanuvchi o‘qituvchi emas"}, status=status.HTTP_403_FORBIDDEN)

        # 1️⃣ Referal daromadlari
        referral_income = TutorReferralTransaction.objects.filter(tutor=tutor).aggregate(
            total=Sum('bonus_amount')
        )['total'] or 0

        # 2️⃣ Kupon keshbeklari
        coupon_income = TutorCouponTransaction.objects.filter(tutor=tutor).aggregate(
            total=Sum('cashback_amount')
        )['total'] or 0

        total_earned = referral_income + coupon_income

        # 3️⃣ Yechilgan va kutilayotgan summalar
        withdrawn = TutorWithdrawal.objects.filter(tutor=tutor, status='approved').aggregate(
            total=Sum('amount')
        )['total'] or 0

        pending = TutorWithdrawal.objects.filter(tutor=tutor, status='pending').aggregate(
            total=Sum('amount')
        )['total'] or 0

        balance = total_earned - withdrawn - pending

        # 4️⃣ Yechib olishlar tarixi
        withdrawals = TutorWithdrawal.objects.filter(tutor=tutor).order_by('-created_at')
        withdrawals_data = TutorWithdrawalSerializer(withdrawals, many=True).data

        data = {
            "total_earned": total_earned,
            "withdrawn": withdrawn,
            "pending": pending,
            "balance": balance,
            "withdrawals": withdrawals_data
        }

        return Response(data, status=status.HTTP_200_OK)
    


class TutorWithdrawalCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tutor = getattr(request.user, 'tutor_profile', None)
        if tutor is None:
            return Response({"error": "Foydalanuvchi o‘qituvchi emas"}, status=status.HTTP_403_FORBIDDEN)

        amount = request.data.get('amount')
        if not amount:
            return Response({"error": "Summani kiriting"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = float(amount)
        except ValueError:
            return Response({"error": "Noto‘g‘ri summa formatida yuborildi"}, status=status.HTTP_400_BAD_REQUEST)

        # === 🔥 LIMIT SETTINGS — DEFAULT & CUSTOM ===
        settings = WithdrawalLimitSettings.objects.first()

        if settings:
            min_limit = float(settings.min_amount)
            max_limit = float(settings.max_amount)
        else:
            # 🔥 Model yo‘q bo‘lsa — default limitlar
            min_limit = 1000
            max_limit = 100000

        # === Minimal tekshiruv ===
        if amount < min_limit:
            return Response(
                {"error": f"Minimal yechib olish miqdori {min_limit} so‘m"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # === Maksimal tekshiruv ===
        if amount > max_limit:
            return Response(
                {"error": f"Maksimal yechib olish miqdori {max_limit} so‘m"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # === Balansni hisoblash ===
        referral_income = TutorReferralTransaction.objects.filter(tutor=tutor).aggregate(
            total=Sum('bonus_amount')
        )['total'] or 0

        coupon_income = TutorCouponTransaction.objects.filter(tutor=tutor).aggregate(
            total=Sum('cashback_amount')
        )['total'] or 0

        withdrawn = TutorWithdrawal.objects.filter(tutor=tutor, status='approved').aggregate(
            total=Sum('amount')
        )['total'] or 0

        pending = TutorWithdrawal.objects.filter(tutor=tutor, status='pending').aggregate(
            total=Sum('amount')
        )['total'] or 0

        balance = referral_income + coupon_income - withdrawn - pending

        # === Balans yetarlimi? ===
        if amount > balance:
            return Response(
                {"error": "Balansda yetarli mablag‘ mavjud emas"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # === Yechib olish so‘rovini yaratish ===
        withdrawal = TutorWithdrawal.objects.create(
            tutor=tutor,
            amount=amount,
            status='pending'
        )

        return Response({
            "message": "Yechib olish so‘rovi yuborildi",
            "withdrawal_id": withdrawal.id
        }, status=status.HTTP_201_CREATED)



class TutorWithdrawalListAPIView(APIView):
    """
    Tizimga kirgan o‘qituvchining barcha yechib olish so‘rovlari ro‘yxati
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        tutor = getattr(request.user, "tutor_profile", None)
        if not tutor:
            return Response(
                {"detail": "Foydalanuvchi o‘qituvchi emas."},
                status=status.HTTP_403_FORBIDDEN
            )

        withdrawals = TutorWithdrawal.objects.filter(tutor=tutor).order_by("-created_at")
        serializer = TutorWithdrawalSerializer(withdrawals, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TutorDetailAPIView(APIView):
    """
    Tutor ID orqali to'liq ma'lumot + kupon orqali ulangan o'quvchilar
    GET /api/v1/tutor/tutor/<id>/detail/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            tutor = Tutor.objects.select_related('user').get(pk=pk)
        except Tutor.DoesNotExist:
            return Response({"detail": "Tutor topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        user = tutor.user

        tutor_data = {
            "profile_id": tutor.id,
            "identification": tutor.identification,
            "full_name": tutor.full_name,
            "phone": user.phone,
            "email": user.email,
            "region": tutor.region,
            "districts": tutor.districts,
            "address": tutor.address,
            "status": tutor.status,
            "device": user.device,
            "registration_date": tutor.tutor_date.strftime('%d/%m/%Y') if tutor.tutor_date else None,
            "registration_time": tutor.tutor_date.strftime('%H:%M:%S') if tutor.tutor_date else None,
        }

        # Tutor kuponi orqali ro'yxatdan o'tgan o'quvchilar
        transactions = TutorCouponTransaction.objects.filter(
            tutor=tutor
        ).select_related('student__user', 'coupon').order_by('-used_at')

        students = []
        for tx in transactions:
            student = tx.student
            students.append({
                "student_id": student.id,
                "identification": student.identification,
                "full_name": student.full_name,
                "phone": student.user.phone,
                "coupon_code": tx.coupon.code,
                "discount_percent": tx.coupon.discount_percent,
                "payment_amount": float(tx.payment_amount),
                "cashback_amount": float(tx.cashback_amount),
                "used_at": tx.used_at.strftime('%d/%m/%Y %H:%M'),
            })

        return Response({
            "tutor": tutor_data,
            "coupon_students_count": len(students),
            "coupon_students": students,
        }, status=status.HTTP_200_OK)