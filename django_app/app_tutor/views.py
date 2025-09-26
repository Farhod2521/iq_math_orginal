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

class TutorCouponViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CouponSerializer

    def get_queryset(self):
        tutor = getattr(self.request.user, 'tutor_profile', None)
        if tutor is None:
            raise PermissionDenied("Foydalanuvchi o‘qituvchi emas")
        return Coupon_Tutor_Student.objects.filter(created_by_tutor=tutor)

    def create(self, request, *args, **kwargs):
        # CouponCreateSerializer bilan validatsiya
        try:
            settings = ReferralAndCouponSettings.objects.latest('updated_at')
        except ReferralAndCouponSettings.DoesNotExist:
            return Response({"error": "ReferralAndCouponSettings topilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CouponCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=settings.coupon_valid_days)

        coupon = serializer.save(
            discount_percent=settings.coupon_discount_percent,
            valid_from=valid_from,
            valid_until=valid_until,
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

    def create(self, request, *args, **kwargs):
        try:
            settings = ReferralAndCouponSettings.objects.latest('updated_at')
        except ReferralAndCouponSettings.DoesNotExist:
            return Response({"error": "ReferralAndCouponSettings topilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReferralCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        valid_from = timezone.now()
        valid_until = valid_from + timedelta(days=settings.referral_valid_days)

        referral = serializer.save(
            bonus_percent=settings.referral_bonus_coin,
            valid_from=valid_from,
            valid_until=valid_until,
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