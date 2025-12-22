# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.conf import settings
from .models import Payment, Subscription, SubscriptionSetting, SubscriptionPlan
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
from .serializers import PaymentSerializer, SubscriptionPlanSerializer, PaymentTeacherSerializer
from django_app.app_student.models import  StudentCouponTransaction
from django_app.app_tutor.models import TutorCouponTransaction
from django_app.app_teacher.models import TeacherCouponTransaction
from django.db.models import Q
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
        original_price = float(plan.price_per_month)
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

        # Keshbek sozlamalari - BARCHA HOLATLAR UCHUN
        cashback_settings = ReferralAndCouponSettings.objects.first()
        
        # ✅ DEFAULT: Hech qanday kupon bo'lmasa, keshbek BERILMAYDI
        student_cashback_amount = 0
        teacher_cashback_amount = 0

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
                    coupon_owner_name = coupon_obj.created_by_tutor.full_name
                    
                    # ✅ TUTOR KUPONI: Faqat tutorga keshbek
                    if cashback_settings:
                        teacher_cashback_percent = cashback_settings.coupon_teacher_cashback_percent
                        teacher_cashback_amount = sale_price * teacher_cashback_percent / 100
                        student_cashback_amount = 0  # Studentga keshbek BERILMAYDI
                    
                elif coupon_obj.created_by_student:
                    coupon_type = "student"
                    coupon_owner_name = coupon_obj.created_by_student.full_name
                    
                    # ✅ STUDENT KUPONI: Faqat studentga (kupon egasi) keshbek
                    if cashback_settings:
                        student_cashback_percent = cashback_settings.coupon_student_cashback_percent
                        student_cashback_amount = sale_price * student_cashback_percent / 100
                        teacher_cashback_amount = 0  # Teacherga keshbek BERILMAYDI
                    
                else:
                    coupon_type = "system"
                    # ✅ SYSTEM KUPONI: Hech kimga keshbek BERILMAYDI
                    student_cashback_amount = 0
                    teacher_cashback_amount = 0
                
                # Sale price hisoblash
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
                    coupon_text = f"IQMATH {discount_percent}% chegirma asosida {plan.get_months_display()} to'lov"
                else:
                    coupon_text = f"IQMATH {discount_percent}% chegirma asosida {plan.get_months_display()} to'lov"
                    
            except Coupon_Tutor_Student.DoesNotExist:
                return Response({"error": "Kupon topilmadi yoki muddati tugagan"}, status=status.HTTP_400_BAD_REQUEST)

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

        # ✅ TO'G'RI KESHBEK QIYMATLARI BILAN TO'LOVNI YARATISH
        payment = Payment.objects.create(
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
            CouponUsage_Tutor_Student.objects.create(
                coupon=coupon_obj,
                used_by_student=student,
                used_by_tutor=coupon_obj.created_by_tutor if coupon_obj.created_by_tutor else None
            )

        return Response({
            "payment_data": response.json(),
            "price_details": {
                "original_price": original_price,
                "sale_price": sale_price,
                "discount_percent": discount_percent,
                "coupon_type": coupon_type,
                "subscription_months": plan.months,
                "subscription_name": plan.get_months_display(),
                "cashback_details": {
                    "student_cashback": student_cashback_amount,
                    "teacher_cashback": teacher_cashback_amount
                }
            }
        }, status=200)

import logging

logger = logging.getLogger(__name__)

class PaymentCallbackAPIView(APIView):
    """
    Multicard to'lov callback API
    """
    authentication_classes = []
    permission_classes = []

    def generate_sign(self, store_id, invoice_id, amount, secret):
        """MD5 signature yaratish"""
        raw = f"{store_id}{invoice_id}{amount}{secret}"
        return hashlib.md5(raw.encode()).hexdigest()

    def post(self, request):
        """
        Multicard dan kelgan to'lov callback ni qayta ishlash
        """
        try:
            # 1. Ma'lumotlarni olish va validatsiya qilish
            data = request.data
            logger.info(f"🔔 Payment callback received: {data}")
            
            store_id = str(data.get("store_id", ""))
            invoice_id = str(data.get("invoice_id", ""))
            amount = str(data.get("amount", ""))
            received_sign = data.get("sign", "")
            payment_time = data.get("payment_time")
            uuid_val = data.get("uuid")
            invoice_uuid = data.get("invoice_uuid")
            billing_id = data.get("billing_id")

            # 2. Signature tekshirish
            SECRET_KEY = "b7lydo1mu8abay9x"
            EXPECTED_SIGN = self.generate_sign(store_id, invoice_id, amount, SECRET_KEY)

            if received_sign != EXPECTED_SIGN:
                logger.error(f"❌ Invalid signature. Expected: {EXPECTED_SIGN}, Received: {received_sign}")
                return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

            # 3. Paymentni topish
            try:
                payment = Payment.objects.get(transaction_id=invoice_id)
                logger.info(f"✅ Payment found: ID={payment.id}, Student={payment.student.full_name}, Amount={payment.amount}")
            except Payment.DoesNotExist:
                logger.error(f"❌ Payment not found with transaction_id: {invoice_id}")
                return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

            # 4. Payment statusini yangilash
            payment.store_id = store_id
            payment.invoice_uuid = invoice_uuid
            payment.uuid = uuid_val
            payment.billing_id = billing_id
            payment.sign = received_sign
            payment.status = "success"
            payment.payment_date = timezone.now()
            payment.receipt_url = f"https://mesh.multicard.uz/invoice/{uuid_val}"
            payment.save()
            logger.info(f"✅ Payment status updated to SUCCESS: {payment.id}")

            # 5. KESHBEK LOGIKASI
            self._process_cashback(payment)

            # 6. SUBSCRIPTION YANGILASH/YARATISH
            self._process_subscription(payment)

            logger.info(f"🎉 Payment callback successfully processed: {payment.id}")
            return Response({"status": "ok", "message": "Payment processed successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"💥 Payment callback error: {str(e)}", exc_info=True)
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _process_cashback(self, payment):
        """Keshbeklarni taqsimlash"""
        try:
            if not payment.coupon or not payment.coupon_type:
                logger.info("ℹ️ No coupon used, skipping cashback processing")
                return

            logger.info(f"💰 Processing cashback for coupon type: {payment.coupon_type}")

            if payment.coupon_type == "tutor" and payment.coupon.created_by_tutor:
                # TUTOR KUPONI: Faqat tutorga keshbek
                if payment.teacher_cashback_amount > 0:
                    TutorCouponTransaction.objects.create(
                        student=payment.student,
                        tutor=payment.coupon.created_by_tutor,
                        coupon=payment.coupon,
                        payment_amount=payment.amount,
                        cashback_amount=payment.teacher_cashback_amount
                    )
                    
                    tutor = payment.coupon.created_by_tutor
                    old_balance = tutor.balance
                    tutor.balance += payment.teacher_cashback_amount
                    tutor.save()
                    
                    logger.info(f"👨‍🏫 Teacher cashback added: {payment.teacher_cashback_amount} to {tutor.full_name} (Balance: {old_balance} -> {tutor.balance})")

            elif payment.coupon_type == "student" and payment.coupon.created_by_student:
                # STUDENT KUPONI: Faqat studentga (kupon egasi) keshbek
                if payment.student_cashback_amount > 0:
                    StudentCouponTransaction.objects.create(
                        student=payment.student,
                        by_student=payment.coupon.created_by_student,
                        coupon=payment.coupon,
                        payment_amount=payment.amount,
                        cashback_amount=payment.student_cashback_amount
                    )
                    
                    student_owner = payment.coupon.created_by_student
                    old_balance = student_owner.balance
                    student_owner.balance += payment.student_cashback_amount
                    student_owner.save()
                    
                    logger.info(f"👨‍🎓 Student cashback added: {payment.student_cashback_amount} to {student_owner.full_name} (Balance: {old_balance} -> {student_owner.balance})")

            elif payment.coupon_type == "system":
                # SYSTEM KUPONI: Hech kimga keshbek berilmaydi
                logger.info("ℹ️ System coupon used, no cashback applied")

                # SYSTEM kuponida transaction tarixini yaratish (cashback yo'q)
                if payment.coupon.created_by_tutor:   # kuponni kim yaratganiga qarab
                    TeacherCouponTransaction.objects.create(
                        student=payment.student,
                        teacher=payment.coupon.created_by_tutor,
                        coupon=payment.coupon,
                        payment_amount=payment.amount
                    )
                    logger.info(f"📝 TeacherCouponTransaction CREATED (system coupon): {payment.coupon.code}")


            # Kupon foydalanish tarixini yozish
            CouponUsage_Tutor_Student.objects.create(
                coupon=payment.coupon,
                used_by_student=payment.student,
                used_by_tutor=payment.coupon.created_by_tutor if payment.coupon.created_by_tutor else None
            )
            logger.info(f"📝 Coupon usage recorded: {payment.coupon.code}")

        except Exception as e:
            logger.error(f"💥 Cashback processing error: {str(e)}", exc_info=True)
            # Cashback xatosi to'lovni to'xtatmasligi kerak

    def _process_subscription(self, payment):
        """Subscriptionni yangilash/yaratish"""
        try:
            now = timezone.now()
            
            # Subscription months ni tekshirish
            subscription_months = payment.subscription_months
            if not subscription_months:
                subscription_months = 1
                logger.warning(f"⚠️ subscription_months not found, using default: {subscription_months}")
            else:
                logger.info(f"📅 Subscription months: {subscription_months}")

            # Subscription mavjudligini tekshirish
            try:
                subscription = Subscription.objects.get(student=payment.student)
                logger.info(f"📋 Existing subscription found: ID={subscription.id}")
                
                # Yangi tugash sanasini hisoblash
                if subscription.end_date and subscription.end_date > now:
                    # Obuna hali amal qilmoqda - muddatni uzaytiramiz
                    new_end_date = subscription.end_date + relativedelta(months=subscription_months)
                    logger.info(f"📈 Extending existing subscription from {subscription.end_date} to {new_end_date}")
                else:
                    # Obuna muddati tugagan - yangi muddat belgilaymiz
                    new_end_date = now + relativedelta(months=subscription_months)
                    logger.info(f"🔄 Subscription expired, setting new end date: {new_end_date}")
                
                # Subscriptionni yangilash
                old_end_date = subscription.end_date
                old_is_paid = subscription.is_paid
                
                subscription.end_date = new_end_date
                subscription.next_payment_date = new_end_date
                subscription.is_paid = True
                subscription.save()
                
                logger.info(f"✅ Subscription UPDATED: EndDate {old_end_date} → {subscription.end_date}, IsPaid {old_is_paid} → {subscription.is_paid}")
                
            except Subscription.DoesNotExist:
                # Yangi subscription yaratish
                new_end_date = now + relativedelta(months=subscription_months)
                
                subscription = Subscription.objects.create(
                    student=payment.student,
                    start_date=now,
                    end_date=new_end_date,
                    next_payment_date=new_end_date,
                    is_paid=True
                )
                
                logger.info(f"✅ NEW Subscription CREATED: ID={subscription.id}, EndDate={subscription.end_date}, IsPaid={subscription.is_paid}")

        except Exception as e:
            logger.error(f"💥 Subscription processing error: {str(e)}", exc_info=True)
            raise  # Subscription xatosi muhim, shuning uchun raise qilamiz









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

        # 🎁 Sinov kunlari
        trial_days_setting = SubscriptionSetting.objects.first()
        trial_days = trial_days_setting.free_trial_days if trial_days_setting else 0

        now = timezone.now()

        # ⏳ Qolgan kunlar
        if now < subscription.end_date:
            remaining_days = (subscription.end_date - now).days
        else:
            remaining_days = 0

        # 💳 To‘lov holati
        is_paid = subscription.is_paid and remaining_days > 0

        # 💰 Eng arzon aktiv reja narxini olish (fallback)
        plan = SubscriptionPlan.objects.filter(is_active=True).order_by('price_per_month').first()
        payment_amount = float(plan.total_price()) if plan else 1000

        # 🔎 Oxirgi muvaffaqiyatli to‘lovni topamiz
        last_payment = (
            Payment.objects
            .filter(student=request.user.student_profile, status="success")
            .order_by('-payment_date', '-created_at')
            .first()
        )

        current_plan_info = None
        if last_payment:
            # To‘lovdan obuna muddatiga qarab tarifni aniqlaymiz
            plan = SubscriptionPlan.objects.filter(
                months=last_payment.subscription_months
            ).first()
            if plan:
                current_plan_info = {
                    "plan_name": plan.get_months_display(),
                    "discount_percent": plan.discount_percent,
                    "total_price": float(plan.total_price()),
                }
            else:
                current_plan_info = {
                    "plan_name": f"{last_payment.subscription_months} oylik (custom)",
                    "discount_percent": last_payment.discount_percent,
                    "total_price": float(last_payment.amount),
                }

        return Response(
            {
                "days_until_next_payment": remaining_days,
                "end_date": subscription.end_date.strftime("%d/%m/%Y"),
                "payment_amount": payment_amount,
                "is_paid": is_paid,
                "current_plan": current_plan_info,  # 🆕 tarif haqida ma’lumot
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
    Kupon kodini tekshiradi, 1 oylik chegirmani hisoblaydi
    va agar kupon allaqachon ishlatilgan bo‘lsa — bloklaydi.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        code = request.data.get("code")
        subscription_id = request.data.get("subscription_id")

        if not code or not subscription_id:
            return Response(
                {"error": "Kupon kodi yoki subscription_id kiritilmadi"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔍 Kuponni olish
        try:
            coupon = Coupon_Tutor_Student.objects.get(code=code)
        except Coupon_Tutor_Student.DoesNotExist:
            return Response(
                {"active": False, "message": "Kupon topilmadi"},
                status=status.HTTP_404_NOT_FOUND
            )

        # ⛔ Kupon yaroqliligini tekshirish
        if not coupon.is_active or not coupon.is_valid():
            return Response(
                {"active": False, "message": "Kupon muddati tugagan yoki faol emas"},
                status=status.HTTP_200_OK
            )

        # 👤 Joriy studentni olish
        student = getattr(request.user, "student_profile", None)
        if not student:
            return Response({"error": "Foydalanuvchi student emas"}, status=403)

        # ⛔ Student o‘z kuponini ishlata olmasin
        if coupon.created_by_student and coupon.created_by_student.id == student.id:
            return Response(
                {"active": False, "message": "Siz o‘zingiz yaratgan kuponni ishlata olmaysiz"},
                status=status.HTTP_403_FORBIDDEN
            )

        # ⛔ Kupon allaqachon shu student tomonidan ishlatilganmi?
        used_in_tutor_tx = TutorCouponTransaction.objects.filter(
            student=student,
            coupon=coupon
        ).exists()
        used_in_teacher_tx = TeacherCouponTransaction.objects.filter(
            student=student,
            coupon=coupon
        ).exists()
        used_in_student_tx = StudentCouponTransaction.objects.filter(
            student=student,
            coupon=coupon
        ).exists()

        if used_in_tutor_tx or used_in_student_tx or used_in_teacher_tx:
            return Response(
                {"active": False, "message": "Ushbu kuponni siz allaqachon ishlatgansiz"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 🎯 Kuponni kim yaratganini aniqlash
        student_id = coupon.created_by_student.id if coupon.created_by_student else None
        tutor_id = coupon.created_by_tutor.id if coupon.created_by_tutor else None

        # 📦 Tarifni olish
        try:
            plan = SubscriptionPlan.objects.get(id=subscription_id)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Tarif topilmadi"}, status=status.HTTP_400_BAD_REQUEST)

        # 💰 Narxlarni hisoblash
        original_price = plan.price_per_month - (plan.price_per_month * plan.discount_percent / 100)
        one_month_plan = SubscriptionPlan.objects.filter(months=1).first()
        one_month_discount = one_month_plan.price_per_month * coupon.discount_percent / 100 if one_month_plan else 0
        sale_price = original_price - one_month_discount
        saved_amount = plan.price_per_month - sale_price

        # 🏷️ Kupon turi
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
            "price": plan.price_per_month,
            "original_price": original_price,
            "sale_price": sale_price,
            "saved_amount": saved_amount,
            "coupon_type": coupon_type
        }, status=status.HTTP_200_OK)

class SubscriptionPlanListAPIView(APIView):

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(
            is_active=True
        ).order_by("months")

        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class PaymentTeacherListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # faqat teacher kirsin
        if not hasattr(user, 'teacher_profile'):
            return Response(
                {"detail": "Sizda bu sahifaga kirish huquqi yo‘q (faqat o‘qituvchilar uchun)."},
                status=status.HTTP_403_FORBIDDEN
            )

        # barcha to‘lovlarni olish (so‘nggi to‘lovlar yuqorida)
        payments = Payment.objects.select_related("student", "coupon").order_by("-created_at")

        # filtrlash parametrlari (ixtiyoriy)
        status_filter = request.GET.get("status")
        coupon_type = request.GET.get("coupon_type")

        if status_filter:
            payments = payments.filter(status=status_filter)
        if coupon_type:
            payments = payments.filter(coupon_type=coupon_type)

        serializer = PaymentTeacherSerializer(payments, many=True)

        # Jadval ko‘rinishida JSON qaytarish
        table_data = {
            "columns": [
                "ID",
                "Student",
                "Amount",
                "Original Amount",
                "Discount (%)",
                "Coupon",
                "Coupon Type",
                "Status",
                "Payment Gateway",
                "Student Cashback",
                "Teacher Cashback",
                "Payment Date",
                "Created At"
            ],
            "rows": serializer.data
        }

        return Response(table_data, status=status.HTTP_200_OK)