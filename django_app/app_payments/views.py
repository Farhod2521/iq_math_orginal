# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.conf import settings
from .models import Payment, Subscription
from datetime import timedelta
import hashlib


class PaymentCallbackAPIView(APIView):
    authentication_classes = []  # Multicard tashqi server bo‘lganligi uchun
    permission_classes = []

    def generate_sign(self, store_id, invoice_id, amount, secret):
        raw = f"{store_id}{invoice_id}{amount}{secret}"
        return hashlib.md5(raw.encode()).hexdigest()

    def post(self, request):
        data = request.data

        store_id = str(data.get("store_id"))
        invoice_id = str(data.get("invoice_id"))
        amount = str(data.get("amount"))
        received_sign = data.get("sign")

        # Sizning secret keyingiz
        SECRET_KEY = "your_secret_key"
        EXPECTED_SIGN = self.generate_sign(store_id, invoice_id, amount, SECRET_KEY)

        if received_sign != EXPECTED_SIGN:
            return Response({"error": "Invalid sign"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(transaction_id=invoice_id)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        # Payment yangilash
        payment.status = "success"
        payment.payment_date = timezone.now()
        payment.save()

        # Subscription yangilash yoki yaratish
        subscription, created = Subscription.objects.get_or_create(student=payment.student)
        subscription.start_date = timezone.now()
        subscription.end_date = subscription.start_date + timedelta(days=30)
        subscription.next_payment_date = subscription.end_date
        subscription.is_paid = True
        subscription.save()

        return Response({"status": "ok"}, status=status.HTTP_200_OK)
