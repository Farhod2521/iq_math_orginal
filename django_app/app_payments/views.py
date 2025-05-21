# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.conf import settings
from .models import Payment, Subscription, SubscriptionSetting
from datetime import timedelta
import hashlib
from .utils import get_multicard_token 
from django_app.app_user.models import Student, User
import requests
import uuid
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from dateutil.relativedelta import relativedelta
from .serializers import PaymentSerializer




class InitiatePaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        amount = 499000

        if not amount:
            return Response({"error": "amount kerak"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({"error": "Talaba topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        # Multicard token olish
        try:
            token = get_multicard_token()
        except Exception as e:
            return Response({"error": "Token olishda xatolik", "details": str(e)}, status=500)

        transaction_id = str(uuid.uuid4())
        headers = {
            "Authorization": f"Bearer {token}"
        }

        # So‘mni tiyin formatiga o‘tkazish
        amount_in_tiyin = int(float(amount) * 100)

        data = {
            "store_id": 6,
            "amount": amount_in_tiyin,
            "invoice_id": transaction_id,
            "return_url": "https://iqmath.uz/",
            "callback_url": "https://backend.iqmath.uz/api/v1/payments/payment-callback/",
            "ofd": [
                {
                    "vat": 12,
                    "price": amount_in_tiyin,
                    "qty": 1,
                    "name": "IQMATH.UZ oylik to'lov",
                    "package_code": "1508099",
                    "mxik": "10202001002000000",
                    "total": amount_in_tiyin
                }
            ]
        }

        try:
            response = requests.post(
                "https://dev-mesh.multicard.uz/payment/invoice",
                headers=headers,
                json=data
            )
        except requests.exceptions.RequestException as e:
            return Response({"error": "Multicard bilan bog‘lanishda xatolik", "details": str(e)}, status=500)

        if response.status_code != 200:
            return Response({"error": "To‘lov yaratilishda xatolik", "details": response.text}, status=500)

        # Bazaga to‘lovni yozib qo‘yamiz
        Payment.objects.create(
            student=student,
            amount=amount,
            transaction_id=transaction_id,
            status="pending",
            payment_gateway="multicard",
        )

        return Response(response.json(), status=200)


class PaymentCallbackAPIView(APIView):
    authentication_classes = []  # Multicard tashqi server bo‘lganligi uchun
    permission_classes = []

    def generate_sign(self, store_id, invoice_id, amount, secret):
        raw = f"{store_id}{invoice_id}{amount}{secret}"
        return hashlib.md5(raw.encode()).hexdigest()

    def post(self, request):
        data = request.data

        # Kelgan ma'lumotlarni olish
        store_id = str(data.get("store_id"))
        invoice_id = str(data.get("invoice_id"))
        amount = str(data.get("amount"))
        received_sign = data.get("sign")
        payment_time = data.get("payment_time")
        uuid = data.get("uuid")
        invoice_uuid = data.get("invoice_uuid")
        billing_id = data.get("billing_id")  # Null bo'lishi mumkin
        sign = data.get("sign")

        # Sizning secret keyingiz
        SECRET_KEY = "Pw18axeBFo8V7NamKHXX"
        EXPECTED_SIGN = self.generate_sign(store_id, invoice_id, amount, SECRET_KEY)

        # Imzo tekshirish
        if received_sign != EXPECTED_SIGN:
            return Response({"error": "Invalid sign"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payment = Payment.objects.get(transaction_id=invoice_id)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
        payment.payment_date = timezone.now()
        payment.payment_time = payment_time
        payment.uuid = uuid
        payment.invoice_uuid = invoice_uuid
        payment.billing_id = billing_id
        payment.sign = sign
        payment.receipt_url = f"https://dev-checkout.multicard.uz/invoice/{uuid}"
        payment.save()

        # Obunani olish yoki yaratish
        subscription, created = Subscription.objects.get_or_create(student=payment.student)

        now = timezone.now()

        if subscription.next_payment_date and subscription.next_payment_date > now:
            # Tekin muddat hali tugamagan — unga 1 oy qo‘shamiz
            subscription.start_date = subscription.next_payment_date
            subscription.end_date = subscription.start_date + relativedelta(months=1)
            subscription.next_payment_date = subscription.end_date
        else:
            # Tekin muddat tugagan yoki yo‘q — hozirgi kundan 1 oy
            subscription.start_date = now
            subscription.end_date = now + relativedelta(months=1)
            subscription.next_payment_date = subscription.end_date

        subscription.is_paid = True
        subscription.save()

        return Response({"status": "ok"}, status=status.HTTP_200_OK)





class SubscriptionTrialDaysAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            subscription = request.user.student_profile.subscription
        except (Student.DoesNotExist, Subscription.DoesNotExist):
            return Response(
                {"detail": "Obuna topilmadi."},
                status=status.HTTP_404_NOT_FOUND
            )

        trial_days = SubscriptionSetting.objects.first().free_trial_days
        now = timezone.now()

        if now < subscription.end_date:
            remaining_days = (subscription.end_date - now).days
        else:
            remaining_days = 0

        return Response(
            {
            "remaining_trial_days": remaining_days,
            "end_date": subscription.end_date.strftime("%Y-%m-%d"),
            "payment_amount": 499000

            },
            status=status.HTTP_200_OK
        )



class MyPaymentsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = request.user.student_profile    # Agar Student modelida OneToOneField bo'lsa
        payments = Payment.objects.filter(student=student)
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)