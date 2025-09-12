# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.conf import settings
from .models import Payment, Subscription, SubscriptionSetting, MonthlyPayment, SubscriptionPlan
from django_app.app_management.models import  Coupon_Tutor_Student, CouponUsage_Tutor_Student, ReferralAndCouponSettings
from datetime import timedelta
import hashlib
from .utils import get_multicard_token 
from django_app.app_user.models import Student, User
import requests
import uuid
from rest_framework.permissions import IsAuthenticated
from datetime import datetime
from dateutil.relativedelta import relativedelta
from .serializers import PaymentSerializer, SubscriptionPlanSerializer
from django_app.app_student.models import  StudentCouponTransaction
from django_app.app_tutor.models import TutorCouponTransaction

URL_TEST = "https://dev-mesh.multicard.uz"
URL_DEV = "https://mesh.multicard.uz"

class InitiatePaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Ma'lumotlarni olish
        subscription_id = request.data.get('subscription_id')
        coupon_code = request.data.get('coupon_code', None)
        
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({"error": "Talaba topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        # Subscription plan tekshirish
        if not subscription_id:
            return Response({"error": "subscription_id kiritilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            plan = SubscriptionPlan.objects.get(id=subscription_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Obuna rejasi topilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        # Asl narxni hisoblash (planning o'zidagi chegirma bilan)
        original_price = float(plan.months * plan.price_per_month)
        if plan.discount_percent > 0:
            original_price = original_price * (1 - plan.discount_percent / 100)

        # Kupon tekshirish
        discount_percent = 0
        coupon_type = None
        coupon_obj = None
        coupon_owner_name = None
        sale_price = original_price
        
        # Standart matn
        coupon_text = f"IQMATH.UZ {plan.get_months_display()} obuna to'lovi"

        if coupon_code:
            try:
                coupon_obj = Coupon_Tutor_Student.objects.get(
                    code=coupon_code, 
                    is_active=True,
                    valid_from__lte=timezone.now(),
                    valid_until__gte=timezone.now()
                )
                
                discount_percent = coupon_obj.discount_percent
                
                # Kupon turini aniqlash
                if coupon_obj.created_by_tutor:
                    coupon_type = "tutor"
                    coupon_owner_name = coupon_obj.created_by_tutor.full_name  # Tutorning o'zidagi full_name
                elif coupon_obj.created_by_student:
                    coupon_type = "student"
                    coupon_owner_name = coupon_obj.created_by_student.full_name  # Studentning o'zidagi full_name
                else:
                    coupon_type = "system"
                
                # Sale price hisoblash (CheckCouponAPIView dagi logika)
                # 1 oylik tarifdan kupon chegirmasi
                one_month_plan = SubscriptionPlan.objects.filter(months=1, is_active=True).first()
                one_month_discount = 0
                if one_month_plan:
                    one_month_price = float(one_month_plan.price_per_month)
                    if one_month_plan.discount_percent > 0:
                        one_month_price = one_month_price * (1 - one_month_plan.discount_percent / 100)
                    one_month_discount = one_month_price * discount_percent / 100

                # Sale price = original_price - 1 oylik kupon chegirma
                sale_price = original_price - one_month_discount
                
                # Matnni yaratish
                if coupon_owner_name:
                    coupon_text = f"IQMATH {discount_percent}% chegirma asosida {plan.get_months_display()} to'lov ({coupon_type.capitalize()}: {coupon_owner_name})"
                else:
                    coupon_text = f"IQMATH {discount_percent}% chegirma asosida {plan.get_months_display()} to'lov"
                    
            except Coupon_Tutor_Student.DoesNotExist:
                return Response({"error": "Kupon topilmadi yoki muddati tugagan"}, status=status.HTTP_400_BAD_REQUEST)

        # Keshbek sozlamalari
        cashback_settings = ReferralAndCouponSettings.objects.first()
        student_cashback_percent = cashback_settings.coupon_student_cashback_percent if cashback_settings else 0
        teacher_cashback_percent = cashback_settings.coupon_teacher_cashback_percent if cashback_settings else 0

        # Keshbek summalarini hisoblash (sale_price asosida)
        student_cashback_amount = sale_price * student_cashback_percent / 100
        teacher_cashback_amount = sale_price * teacher_cashback_percent / 100

        # Token olish
        try:
            token = get_multicard_token()
        except Exception as e:
            return Response({"error": "Token olishda xatolik", "details": str(e)}, status=500)

        # Tranzaksiya ID yaratish
        transaction_id = str(uuid.uuid4())
        headers = {"Authorization": f"Bearer {token}"}
        amount_in_tiyin = int(sale_price * 100)
        
        # Multicardga jo'natiladigan ma'lumotlar
        data = {
            "store_id": 1915,
            "amount": amount_in_tiyin,
            "invoice_id": transaction_id,
            "return_url": "https://iqmath.uz/",
            "callback_url": "https://backend.iqmath.uz/api/v1/payments/payment-callback/",
            "ofd": [
                {
                    "vat": 0,
                    "price": amount_in_tiyin,
                    "qty": 1,
                    "name": coupon_text,
                    "package_code": "1508099",
                    "mxik": "10202001002000000",
                    "total": amount_in_tiyin
                }
            ]
        }

        # Multicardga so'rov yuborish
        try:
            response = requests.post(f"{URL_DEV}/payment/invoice", headers=headers, json=data)
        except requests.exceptions.RequestException as e:
            return Response({"error": "Multicard bilan bog'lanishda xatolik", "details": str(e)}, status=500)

        if response.status_code != 200:
            return Response({"error": "To'lov yaratilishda xatolik", "details": response.text}, status=500)

        # To'lovni bazaga yozish
        Payment.objects.create(
            student=student,
            amount=sale_price,
            original_amount=original_price,
            transaction_id=transaction_id,
            status="pending",
            payment_gateway="multicard",
            coupon=coupon_obj,
            coupon_type=coupon_type,
            discount_percent=discount_percent,
            student_cashback_amount=student_cashback_amount,
            teacher_cashback_amount=teacher_cashback_amount,
            subscription_months=plan.months
        )

        # Agar kupon ishlatilgan bo'lsa, foydalanish tarixini yozish
        if coupon_obj:
            student_id = coupon_obj.created_by_student.id if coupon_obj.created_by_student else None
            tutor_id = coupon_obj.created_by_tutor.id if coupon_obj.created_by_tutor else None
            
            CouponUsage_Tutor_Student.objects.create(
                coupon=coupon_obj,
                used_by_student=student if student_id else None,
                used_by_tutor=coupon_obj.created_by_tutor if tutor_id else None
            )

        return Response({
            "payment_data": response.json(),
            "price_details": {
                "original_price": original_price,
                "sale_price": sale_price,
                "discount_percent": discount_percent,
                "coupon_type": coupon_type,
                "subscription_months": plan.months,
                "subscription_name": plan.get_months_display()
            }
        }, status=200)

class PaymentCallbackAPIView(APIView):
    authentication_classes = []
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
        payment_time = data.get("payment_time")
        uuid_val = data.get("uuid")
        invoice_uuid = data.get("invoice_uuid")
        billing_id = data.get("billing_id")

        SECRET_KEY = "b7lydo1mu8abay9x"
        EXPECTED_SIGN = self.generate_sign(store_id, invoice_id, amount, SECRET_KEY)

        if received_sign != EXPECTED_SIGN:
            return Response({"error": "Invalid sign"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(transaction_id=invoice_id)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        # Update payment status
        payment.status = "success"
        payment.payment_date = timezone.now()
        payment.payment_time = payment_time
        payment.uuid = uuid_val
        payment.invoice_uuid = invoice_uuid
        payment.billing_id = billing_id
        payment.sign = received_sign
        payment.receipt_url = f"{URL_DEV}/invoice/{uuid_val}"
        payment.save()

        # Create coupon transaction if coupon was used
        if payment.coupon and payment.coupon_type:
            cashback_settings = ReferralAndCouponSettings.objects.first()
            
            if payment.coupon_type == "tutor" and payment.coupon.created_by_tutor:
                TutorCouponTransaction.objects.create(
                    student=payment.student,
                    tutor=payment.coupon.created_by_tutor,
                    coupon=payment.coupon,
                    payment_amount=payment.amount,
                    student_cashback_amount=payment.student_cashback_amount,
                    teacher_cashback_amount=payment.teacher_cashback_amount
                )
                
                # Add cashback to tutor's balance
                if payment.teacher_cashback_amount > 0:
                    payment.coupon.created_by_tutor.balance += payment.teacher_cashback_amount
                    payment.coupon.created_by_tutor.save()

            elif payment.coupon_type == "student" and payment.coupon.created_by_student:
                StudentCouponTransaction.objects.create(
                    student=payment.student,
                    by_student=payment.coupon.created_by_student,
                    coupon=payment.coupon,
                    payment_amount=payment.amount,
                    student_cashback_amount=payment.student_cashback_amount,
                    teacher_cashback_amount=payment.teacher_cashback_amount
                )
                
                # Add cashback to student's balance
                if payment.student_cashback_amount > 0:
                    payment.coupon.created_by_student.balance += payment.student_cashback_amount
                    payment.coupon.created_by_student.save()

            # Add cashback to paying student
            if payment.student_cashback_amount > 0:
                payment.student.balance += payment.student_cashback_amount
                payment.student.save()

        # Create or update subscription
        subscription, created = Subscription.objects.get_or_create(student=payment.student)
        now = timezone.now()
        
        if created:
            subscription.start_date = now
            subscription.end_date = now + relativedelta(months=payment.subscription_months or 1)
        else:
            if subscription.end_date > now:
                subscription.end_date += relativedelta(months=payment.subscription_months or 1)
            else:
                subscription.end_date = now + relativedelta(months=payment.subscription_months or 1)

        subscription.next_payment_date = subscription.end_date + relativedelta(months=1)
        subscription.is_paid = True
        subscription.save()

        return Response({"status": "ok"}, status=status.HTTP_200_OK)


































# class InitiatePaymentAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         # Bazadan oylik to'lov narxini olish
#         monthly_payment = MonthlyPayment.objects.first()
#         base_amount = monthly_payment.price if monthly_payment else 1000

#         # request.data dan amount olish, agar yuborilmagan bo'lsa bazadagi qiymat
#         amount = request.data.get('amount', base_amount)

#         coupon_code = request.data.get('coupon', None)

#         if not amount:
#             return Response({"error": "amount kerak"}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             student = Student.objects.get(user=request.user)
#         except Student.DoesNotExist:
#             return Response({"error": "Talaba topilmadi"}, status=status.HTTP_404_NOT_FOUND)

#         discount_percent = 0
#         coupon_text = "IQMATH.UZ oylik to'lov"

#         # Kupon kodni tekshirish
#         if coupon_code:
#             try:
#                 coupon = SystemCoupon.objects.get(code=coupon_code, is_active=True)
#                 if coupon.valid_until > timezone.now():
#                     discount_percent = coupon.discount_percent
#                     coupon_text = f"IQMATH {discount_percent}% chegirma asosida oylik to'lov"
#                 else:
#                     return Response({"error": "Kupon muddati tugagan"}, status=status.HTTP_400_BAD_REQUEST)
#             except SystemCoupon.DoesNotExist:
#                 return Response({"error": "Kupon topilmadi yoki faolligi yo‘q"}, status=status.HTTP_400_BAD_REQUEST)

#         # Chegirmadan so‘ng hisoblash
#         discounted_amount = float(amount)
#         if discount_percent > 0:
#             discounted_amount = discounted_amount * (1 - discount_percent / 100)

#         # Token olish va to‘lov yaratish jarayoni...

#         try:
#             token = get_multicard_token()
#         except Exception as e:
#             return Response({"error": "Token olishda xatolik", "details": str(e)}, status=500)

#         transaction_id = str(uuid.uuid4())
#         headers = {
#             "Authorization": f"Bearer {token}"
#         }

#         amount_in_tiyin = int(discounted_amount * 100)

#         data = {
#             "store_id": 1915,
#             "amount": amount_in_tiyin,
#             "invoice_id": transaction_id,
#             "return_url": "https://iqmath.uz/",
#             "callback_url": "https://backend.iqmath.uz/api/v1/payments/payment-callback/",
#             "ofd": [
#                 {
#                     "vat": 0,
#                     "price": amount_in_tiyin,
#                     "qty": 1,
#                     "name": coupon_text,
#                     "package_code": "1508099",
#                     "mxik": "10202001002000000",
#                     "total": amount_in_tiyin
#                 }
#             ]
#         }

#         try:
#             response = requests.post(
#                 f"{URL_DEV}/payment/invoice",
#                 headers=headers,
#                 json=data
#             )
#         except requests.exceptions.RequestException as e:
#             return Response({"error": "Multicard bilan bog‘lanishda xatolik", "details": str(e)}, status=500)

#         if response.status_code != 200:
#             return Response({"error": "To‘lov yaratilishda xatolik", "details": response.text}, status=500)

#         Payment.objects.create(
#             student=student,
#             amount=discounted_amount,
#             transaction_id=transaction_id,
#             status="pending",
#             payment_gateway="multicard",
#         )

#         return Response(response.json(), status=200)



# class PaymentCallbackAPIView(APIView):
#     authentication_classes = []  # Multicard tashqi server bo‘lganligi uchun
#     permission_classes = []

#     def generate_sign(self, store_id, invoice_id, amount, secret):
#         raw = f"{store_id}{invoice_id}{amount}{secret}"
#         return hashlib.md5(raw.encode()).hexdigest()

#     def post(self, request):
#         data = request.data

#         # Kelgan ma'lumotlarni olish
#         store_id = str(data.get("store_id"))
#         invoice_id = str(data.get("invoice_id"))
#         amount = str(data.get("amount"))
#         received_sign = data.get("sign")
#         payment_time = data.get("payment_time")
#         uuid = data.get("uuid")
#         invoice_uuid = data.get("invoice_uuid")
#         billing_id = data.get("billing_id")  # Null bo'lishi mumkin
#         sign = data.get("sign")

#         # Sizning secret keyingiz
#         SECRET_KEY = "b7lydo1mu8abay9x"
#         EXPECTED_SIGN = self.generate_sign(store_id, invoice_id, amount, SECRET_KEY)

#         # Imzo tekshirish
#         if received_sign != EXPECTED_SIGN:
#             return Response({"error": "Invalid sign"}, status=status.HTTP_400_BAD_REQUEST)
#         try:
#             payment = Payment.objects.get(transaction_id=invoice_id)
#         except Payment.DoesNotExist:
#             return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)
#         payment.status = "success"
#         payment.payment_date = timezone.now()
#         payment.payment_time = payment_time
#         payment.uuid = uuid
#         payment.invoice_uuid = invoice_uuid
#         payment.billing_id = billing_id
#         payment.sign = sign
#         payment.receipt_url = f"{URL_DEV}/invoice/{uuid}"
#         payment.save()

#         # Obunani yaratish yoki olish
#         subscription, created = Subscription.objects.get_or_create(student=payment.student)

#         now = timezone.now()

#         if created:
#             # Agar yangi bo‘lsa, hozirgi vaqtdan boshlab 1 oy qo‘shiladi
#             subscription.start_date = now
#             subscription.end_date = now + relativedelta(months=1)
#         else:
#             # Agar mavjud bo‘lsa, end_date tekshiriladi
#             if subscription.end_date > now:
#                 # Obuna muddati hali tugamagan bo‘lsa, end_date ga 1 oy qo‘shiladi
#                 subscription.end_date += relativedelta(months=1)
#             else:
#                 # Obuna muddati tugagan bo‘lsa, hozirgi vaqtdan boshlab 1 oy belgilanadi
#                 subscription.end_date = now + relativedelta(months=1)

#         # next_payment_date yangi end_date ga 1 oy qo‘shib belgilanadi
#         subscription.next_payment_date = subscription.end_date + relativedelta(months=1)
#         subscription.is_paid = True
#         subscription.save()

#         return Response({"status": "ok"}, status=status.HTTP_200_OK)





from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import MonthlyPayment, Student, Subscription, SubscriptionSetting  # mos importlar

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

        trial_days_setting = SubscriptionSetting.objects.first()
        trial_days = trial_days_setting.free_trial_days if trial_days_setting else 0

        now = timezone.now()

        if now < subscription.end_date:
            remaining_days = (subscription.end_date - now).days
        else:
            remaining_days = 0

        # is_paid flag logikasi
        is_paid = subscription.is_paid and remaining_days > 0

        # MonthlyPayment modeldan narx olish
        monthly_payment = MonthlyPayment.objects.first()
        payment_amount = monthly_payment.price if monthly_payment else 1000

        return Response(
            {
                "days_until_next_payment": remaining_days,
                "end_date": subscription.end_date.strftime("%d/%m/%Y"),
                "payment_amount": payment_amount,
                "is_paid": is_paid
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
    
class CheckCouponAPIView(APIView):
    """
    Kupon kodini tekshiradi va 1 oylik chegirmani alohida hisoblaydi.
    """

    def post(self, request, *args, **kwargs):
        code = request.data.get("code")
        subscription_id = request.data.get("subscription_id")

        if not code or not subscription_id:
            return Response({"error": "Kupon kodi yoki subscription_id kiritilmadi"}, status=400)

        # Kuponni olish
        try:
            coupon = Coupon_Tutor_Student.objects.get(code=code)
        except Coupon_Tutor_Student.DoesNotExist:
            return Response({"active": False, "message": "Kupon topilmadi"}, status=404)

        if not coupon.is_active or not coupon.is_valid():
            return Response({"active": False, "message": "Kupon muddati tugagan yoki faol emas"}, status=200)

        # Kuponni kim yaratganini aniqlash
        student_id = coupon.created_by_student.id if coupon.created_by_student else None
        tutor_id = coupon.created_by_tutor.id if coupon.created_by_tutor else None

        # Allaqachon ishlatilganmi
        # already_used = CouponUsage_Tutor_Student.objects.filter(
        #     coupon=coupon,
        #     used_by_student_id=student_id,
        #     used_by_tutor_id=tutor_id
        # ).exists()
        # if already_used:
        #     return Response({"active": False, "message": "Kupon avval ishlatilgan"}, status=200)

        # Tanlangan tarif
        try:
            plan = SubscriptionPlan.objects.get(id=subscription_id)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Tarif topilmadi"}, status=400)

        original_price = plan.price_per_month - (plan.price_per_month * plan.discount_percent / 100)

        # 1 oylik tarifdan kupon chegirmasi
        one_month_plan = SubscriptionPlan.objects.filter(months=1).first()
        one_month_discount = 0
        if one_month_plan:
            one_month_discount = one_month_plan.price_per_month * coupon.discount_percent / 100

        # Sale price = original_price - 1 oylik kupon chegirma
        sale_price = original_price - one_month_discount

        # Tejalgan summa
        saved_amount = plan.price_per_month - sale_price
        price = plan.price_per_month
        # Foydalanish tarixini yozish
        CouponUsage_Tutor_Student.objects.create(
            coupon=coupon,
            used_by_student_id=student_id,
            used_by_tutor_id=tutor_id
        )
        if coupon.created_by_student:
            coupon_type = "student"
        elif coupon.created_by_tutor:
            coupon_type = "tutor"
        else:
            coupon_type = "system"
        return Response({
            "active": True,
            "code": coupon.code,
            "discount_percent": coupon.discount_percent,
            "price": price,
            "original_price": original_price,
            "sale_price": sale_price,
            "saved_amount": saved_amount,
            "coupon_type": coupon_type
        }, status=200)


class SubscriptionPlanListAPIView(APIView):
    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('months')
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data)