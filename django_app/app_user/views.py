from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import StudentRegisterSerializer, VerifySmsCodeSerializer, LoginSerializer, StudentProfileSerializer
from .models import Student, UserSMSAttempt  
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings
from datetime import timedelta
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
import jwt
from django.shortcuts import get_object_or_404
from .sms_service import send_sms, send_verification_email, send_sms_resend
from django.contrib.auth import get_user_model
import random
from django.contrib.auth.hashers import make_password
from django.utils.timezone import now
from rest_framework.generics import  ListAPIView, UpdateAPIView
from .sms_service import send_login_parol_resend_email
User = get_user_model()





class RegisterStudentAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = StudentRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Telefon raqamga SMS kodi yuborildi. Kodni tasdiqlang."}, status=status.HTTP_200_OK)
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(APIView):
    """
    Foydalanuvchi parolni unutganini so'raganida SMS yuboradi.
    """
    def post(self, request):
        phone = request.data.get("phone")  # Telefon raqami olish
        email = request.data.get("email")  # Email manzili olish
        
        # Telefon yoki emaildan faqat biri kelsa, qaysi biri kelyapti, shuni tekshiramiz
        if not phone and not email:
            return Response({"error": "Telefon raqami yoki email manzilini kiriting."}, status=status.HTTP_400_BAD_REQUEST)
        
        user = None
        if phone:
            # Agar telefon raqami bo‘lsa, uni tekshiramiz
            user = User.objects.filter(phone=phone).first()
        elif email:
            # Agar email bo‘lsa, uni tekshiramiz
            user = User.objects.filter(email=email).first()

        if not user:
            return Response({"error": "Bu telefon raqami yoki email bilan foydalanuvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        
        # SMS yuborishdan oldin foydalanuvchining SMS yuborish imkoniyati mavjudligini tekshirish
        can_send, remaining_time = UserSMSAttempt.can_send_sms(user)
        
        if not can_send:
            remaining_time_str = str(remaining_time).split(".")[0]  # Qolgan vaqtni faqat to‘liq soat, daqiqa va sekundlarda ko‘rsatish
            return Response({
                "error": f"Siz hozirda SMS kodini olish imkoniyatiga ega emassiz. Keyinroq urinib ko'ring.",
                "retry_after": remaining_time_str
            }, status=status.HTTP_400_BAD_REQUEST)
        sms_code = str(random.randint(10000, 99999))
        user.sms_code = sms_code
        # user.set_unusable_password()  # SMS orqali login qilish imkoniyati uchun parolsiz qilish
        user.save()

        # SMS yuborish (send_sms funksiyasini moslashtiring)
        if phone:
            send_sms_resend(user.phone, sms_code)  # Telefon raqamiga SMS yuborish
        # elif email:
        #     send_email(user.email, sms_code)  # Email manziliga SMS yuborish (email orqali yuborilsa)
        UserSMSAttempt.register_attempt(user)

        return Response({"message": "SMS kodi yuborildi. Iltimos, uni tekshirib ko'ring."}, status=status.HTTP_200_OK)

class VerifySMSCodeView(APIView):
    """
    Foydalanuvchi SMS kodini kiritib, uni tasdiqlaydi.
    """
    def post(self, request):
        phone = request.data.get("phone")  # Telefon raqami olish
        email = request.data.get("email")  # Email manzili olish
        sms_code = request.data.get("sms_code")  # Foydalanuvchi kiritgan SMS kodini olish

        if not sms_code:
            return Response({"error": "Iltimos, SMS kodini kiriting."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Telefon yoki emaildan faqat biri kelsa, qaysi biri kelyapti, shuni tekshiramiz
        if not phone and not email:
            return Response({"error": "Telefon raqami yoki email manzilini kiriting."}, status=status.HTTP_400_BAD_REQUEST)
        
        user = None
        if phone:
            user = User.objects.filter(phone=phone).first()
        elif email:
            user = User.objects.filter(email=email).first()

        if not user:
            return Response({"error": "Bu telefon raqami yoki email bilan foydalanuvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        # SMS kodini tekshirish
        if user.sms_code != sms_code:
            return Response({"error": "Noto'g'ri SMS kodi kiritildi."}, status=status.HTTP_400_BAD_REQUEST)

        # SMS kodi to'g'ri, foydalanuvchiga yangi parol o'rnatish imkoniyatini berish
        user.set_unusable_password()  # SMS orqali kirish imkoniyatini yaratish uchun

        return Response({
            "message": "SMS kodi tasdiqlandi. Iltimos, yangi parolni kiriting."
        }, status=status.HTTP_200_OK)

class ResetPasswordView(APIView):
    """
    Foydalanuvchi yangi parolni o'rnatadi.
    """
    def post(self, request):
        phone = request.data.get("phone")  # Telefon raqami olish
        email = request.data.get("email")  # Email manzili olish
        new_password = request.data.get("new_password")  # Yangi parolni olish

        if not new_password:
            return Response({"error": "Iltimos, yangi parolni kiriting."}, status=status.HTTP_400_BAD_REQUEST)

        # Telefon yoki emaildan faqat biri kelsa, qaysi biri kelyapti, shuni tekshiramiz
        if not phone and not email:
            return Response({"error": "Telefon raqami yoki email manzilini kiriting."}, status=status.HTTP_400_BAD_REQUEST)
        
        user = None
        if phone:
            user = User.objects.filter(phone=phone).first()
        elif email:
            user = User.objects.filter(email=email).first()

        if not user:
            return Response({"error": "Bu telefon raqami yoki email bilan foydalanuvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        # Yangi parolni o'rnatish
        user.password = make_password(new_password)  # Yangi parolni saqlash
        user.sms_code = None  # SMS kodi nolga o'rnatiladi
        user.save()
        send_login_parol_resend_email(user.email, phone, new_password)

        return Response({
            "message": "Parol muvaffaqiyatli yangilandi."
        }, status=status.HTTP_200_OK)



class ResendSMSCodeView(APIView):
    """
    Foydalanuvchiga yangi SMS kodi yuborish.
    """
    def post(self, request):
        phone = request.data.get("phone")  # Telefon raqami olish
        email = request.data.get("email")  # Email manzili olish

        # Telefon yoki emaildan faqat biri kelsa, qaysi biri kelyapti, shuni tekshiramiz
        if not phone and not email:
            return Response({"error": "Telefon raqami yoki email manzilini kiriting."}, status=status.HTTP_400_BAD_REQUEST)

        user = None
        if phone:
            user = User.objects.filter(phone=phone).first()
        elif email:
            user = User.objects.filter(email=email).first()

        if not user:
            return Response({"error": "Bu telefon raqami yoki email bilan foydalanuvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        # SMS yuborishdan oldin foydalanuvchining SMS yuborish imkoniyati mavjudligini tekshirish
        can_send, remaining_time = UserSMSAttempt.can_send_sms(user)

        if not can_send:
            remaining_time_str = str(remaining_time).split(".")[0]  # Qolgan vaqtni faqat to‘liq soat, daqiqa va sekundlarda ko‘rsatish
            return Response({
                "error": f"Siz hozirda SMS kodini olish imkoniyatiga ega emassiz. Keyinroq urinib ko'ring.",
                "retry_after": remaining_time_str
            }, status=status.HTTP_400_BAD_REQUEST)

        # Yangi SMS kodi yaratish
        sms_code = str(random.randint(10000, 99999))
        user.sms_code = sms_code
        user.save()

        # SMS yuborish (send_sms funksiyasini moslashtiring)
        if phone:
            send_sms(user.phone, sms_code)
        if user.email:
            send_verification_email(user.email, sms_code)  

        UserSMSAttempt.register_attempt(user)

        return Response({
            "message": "Yangi SMS kodi yuborildi. Iltimos, uni tekshirib ko'ring."
        }, status=status.HTTP_200_OK)

class StudentProfileAPIView(APIView):

    def get(self, request, *args, **kwargs):
        token_header = request.headers.get('Authorization', '')
        if not token_header or not token_header.startswith('Bearer '):
            return Response({"error": "Authorization token missing or invalid"}, status=status.HTTP_401_UNAUTHORIZED)

        token = token_header.split(' ')[1]

        try:
            decoded_token = jwt.decode(token, options={"verify_signature": False})
        except jwt.DecodeError:
            return Response({"error": "Failed to decode token"}, status=status.HTTP_401_UNAUTHORIZED)

   
        student_id = decoded_token.get('student_id')
      
        if not student_id:
            raise AuthenticationFailed('Student ID not found in token')


        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"error": "Student profile not found"}, status=404)
        student_datetime = student.student_date  # Studentning vaqt maydoni
        ashgabat_tz = pytz.timezone("Asia/Ashgabat") 
        if student_datetime:
            student_datetime = student_datetime.astimezone(ashgabat_tz)
            student_date = student_datetime.strftime('%Y-%m-%d')  # YYYY-MM-DD
            student_time = student_datetime.strftime('%H:%M:%S')  # HH:MM:SS
        else:
            student_date = None
            student_time = None
        data = {
                'full_name': student.full_name,
                'phone': student.user.phone if hasattr(student.user, 'phone') else None,
                'email': student.user.email if hasattr(student.user, 'email') else None,
                'region': student.region,
                'districts': student.districts,
                'address': student.address,
                'brithday': student.brithday,
                'academy_or_school': student.academy_or_school,
                'academy_or_school_name': student.academy_or_school_name,
                'class_name': student.class_name,
                'address': student.address,
                'document_type': student.document_type,
                'document': student.document,
                'type_of_education': student.type_of_education,
                'student_date': student_date,  # YYYY-MM-DD (UTC+5)
                'student_time': student_time,  # HH:MM:SS (UTC+5)
        }

        return Response(data)


from django.utils.timezone import localtime
import pytz
from rest_framework.permissions import IsAuthenticated
class StudentsListView(APIView): 
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ashgabat_tz = pytz.timezone("Asia/Ashgabat")  # UTC+5 vaqt zonasi

        # Faqat roli 'student' bo'lgan foydalanuvchilarni olish
        students = Student.objects.filter(user__role='student', status=True)

        data = []
        for student in students:
            student_datetime = student.student_date  # Studentning vaqt maydoni

            if student_datetime:
                # UTC vaqtni UTC+5 (Ashgabat) ga o‘girish
                student_datetime = student_datetime.astimezone(ashgabat_tz)
                student_date = student_datetime.strftime('%Y-%m-%d')  # YYYY-MM-DD
                student_time = student_datetime.strftime('%H:%M:%S')  # HH:MM:SS
            else:
                student_date = None
                student_time = None

            data.append({
                'full_name': student.full_name,
                'phone': student.user.phone,
                'email': student.user.email,
                'region': student.region,
                'districts': student.districts,
                'address': student.address,
                'brithday': student.brithday,
                'academy_or_school': student.academy_or_school,
                'academy_or_school_name': student.academy_or_school_name,
                'class_name': student.class_name,
                'document_type': student.document_type,
                'document': student.document,
                'type_of_education': student.type_of_education,
                'student_date': student_date,  # YYYY-MM-DD (UTC+5)
                'student_time': student_time,  # HH:MM:SS (UTC+5)
            })

        return Response(data)




class VerifySmsCodeAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = VerifySmsCodeSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]

            try:
                student = Student.objects.get(user=user)
            except Student.DoesNotExist:
                return Response({"detail": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

            # **Eski sessiyalarni o‘chirish**
            UserSession.objects.filter(user=user).delete()

            # **JWT Token yaratish**
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            access_token.set_exp(lifetime=timedelta(hours=3))
            access_token['student_id'] = student.id
            expires_in = timedelta(hours=3).total_seconds()

            # **Foydalanuvchining qurilma ma’lumotlarini olish**
            device = request.headers.get('User-Agent', 'Unknown Device')
            ip_address = request.META.get('REMOTE_ADDR', '0.0.0.0')

            # **Yangi sessiyani yaratish**
            user_session = UserSession.objects.create(
                user=user,
                device=device,
                browser=device,  # Agar alohida browser olish bo'lsa, user-agentdan parsing qilish kerak
                ip_address=ip_address,
                token=str(access_token)  # Tokenni saqlash
            )

            return Response({
                "message": "Ro'yxatdan o'tish muvaffaqiyatli yakunlandi.",
                "login": serializer.validated_data['phone'],
                "password": serializer.validated_data['password'],
                "access_token": str(access_token),
                "expires_in": expires_in,
                "user_session_id": user_session.id
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



from user_agents import parse
from django.contrib.sessions.models import Session
from django.db import transaction
import user_agents 

class LoginAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            try:
                student = Student.objects.get(user=user)
            except Student.DoesNotExist:
                return Response({"detail": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

            # # # Qurilma va brauzer ma'lumotlarini olish
            # user_agent = request.META.get("HTTP_USER_AGENT", "")
            # device_info = parse(user_agent)
            # device_name = f"{device_info.device.brand} {device_info.device.family}"
            # browser_name = f"{device_info.browser.family} {device_info.browser.version_string}"
            # ip_address = request.META.get("REMOTE_ADDR")

            # # Foydalanuvchining avvalgi sessiyasini tekshirish
            # existing_session = UserSession.objects.filter(user=user).first()

            # if existing_session:
            #     # Agar foydalanuvchi boshqa qurilmadan kirsa, xabar qaytariladi
            #     if existing_session.device != device_name or existing_session.browser != browser_name:
            #         return Response({"detail": "Siz allaqachon boshqa qurilmadan tizimga kirgansiz!"}, 
            #                         status=status.HTTP_403_FORBIDDEN)

            #     # Eski tokenni o‘chirish
            #     existing_session.delete()

            # Yangi sessiya uchun token yaratish
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            access_token.set_exp(lifetime=timedelta(hours=13))
            access_token['student_id'] = student.id

            # Yangi sessiyani bazaga yozish
            # with transaction.atomic():
            #     user_session = UserSession.objects.create(
            #         user=user,
            #         device=device_name,
            #         browser=browser_name,
            #         ip_address=ip_address,
            #         token=str(access_token)
            #     )

            expires_in = timedelta(hours=13).total_seconds()

            # Foydalanuvchining sessiya ma'lumotlarini qaytarish
            student_data = {
                "id": student.id,
                "full_name": student.full_name,
                "email": user.email,
                "phone": user.phone,
                "region": student.region,
                "districts": student.districts,
                "address": student.address,
                "brithday": student.brithday,
                "academy_or_school": student.academy_or_school,
                "class_name": student.class_name,
                "role": user.role,
                "status": student.status,
                "access_token": str(access_token),
                "expires_in": expires_in,
            }

            return Response(student_data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_client_ip(self, request):
        """Foydalanuvchining IP-manzilini olish"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def get_device_info(self, request):
        """Foydalanuvchining qurilmasi haqida ma’lumot olish"""
        user_agent_string = request.META.get("HTTP_USER_AGENT", "")
        user_agent = user_agents.parse(user_agent_string)

        device_type = "Mobile" if user_agent.is_mobile else "Tablet" if user_agent.is_tablet else "Desktop"
        os = user_agent.os.family  
        browser = user_agent.browser.family  

        return {
            "device_type": device_type,
            "os": os,
            "browser": browser,
        }




class LogoutDeviceAPIView(APIView):
    def post(self, request):
        """Tanlangan qurilmani tizimdan chiqarib yuborish"""
        session_key = request.data.get("session_key")  # Frontenddan kelgan session ID

        if not session_key:
            return Response({"detail": "session_key majburiy!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_session = UserSession.objects.get(session_key=session_key)

            # Django sessiyasini o‘chirish
            if user_session.session_key:
                from django.contrib.sessions.models import Session
                Session.objects.filter(session_key=user_session.session_key).delete()

            # UserSession jadvalidan ushbu qurilmani o‘chirish
            user_session.delete()

            return Response({"detail": "Qurilma tizimdan chiqarildi."}, status=status.HTTP_200_OK)

        except UserSession.DoesNotExist:
            return Response({"detail": "Sessiya topilmadi."}, status=status.HTTP_404_NOT_FOUND)