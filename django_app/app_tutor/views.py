from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets, permissions, status
from django.utils import timezone
from datetime import timedelta
from django_app.app_management.models import  Coupon_Tutor_Student, ReferralAndCouponSettings, Referral_Tutor_Student
from .serializers import (
    CouponCreateSerializer, ReferralCreateSerializer, 
      TutorCouponTransactionSerializer, TutorReferralTransactionSerializer,
      CouponSerializer, ReferralSerializer)
from django.db import IntegrityError
from rest_framework.exceptions import PermissionDenied
from .models import TutorCouponTransaction, TutorReferralTransaction
import random
import string

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
            return Response({"error": "Foydalanuvchi O‘qituvchi emas"}, status=status.HTTP_403_FORBIDDEN)

        transactions = TutorReferralTransaction.objects.filter(tutor=tutor).select_related('student', 'referral')
        serializer = TutorReferralTransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)