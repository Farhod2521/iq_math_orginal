from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
StudentRegisterSerializer, VerifySmsCodeSerializer, 
LoginSerializer, StudentProfileSerializer, TeacherRegisterSerializer, Class_Serializer,
TeacherVerifySmsCodeSerializer, TeacherSerializer, StudentSerializer
)
from .models import Student, UserSMSAttempt, Teacher, Class, StudentLoginHistory
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
from django_app.app_student.models import Diagnost_Student
User = get_user_model()









##############################################################
###################     CLASS NAME LIST VIEW    ##############
##############################################################
class ClassListView(ListAPIView):
    queryset = Class.objects.all()
    serializer_class = Class_Serializer








##############################################################
###################     TEACHERS    REGISTER   ###############
##############################################################

class RegisterTeacherAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = TeacherRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Telefon raqamga SMS kodi yuborildi. Kodni tasdiqlang."},
                status=status.HTTP_200_OK
            )
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

##############################################################
###################     TEACHERS    LOGIN     ###############
##############################################################
class TeacherLoginAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            try:
                teacher = Teacher.objects.get(user=user)
            except Teacher.DoesNotExist:
                return Response({"detail": "Teacher profile not found."}, status=status.HTTP_404_NOT_FOUND)
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            access_token.set_exp(lifetime=timedelta(hours=13))
            access_token['teacher_id'] = teacher.id
            expires_in = timedelta(hours=13).total_seconds()

            # Foydalanuvchining sessiya ma'lumotlarini qaytarish
            teacher_data = {
                "id": teacher.id,
                "full_name": teacher.full_name,
                "email": user.email,
                "phone": user.phone,
                "region": teacher.region,
                "districts": teacher.districts,
                "address": teacher.address,
                "brithday": teacher.brithday,
                "role": user.role,
                "status": teacher.status,
                "access_token": str(access_token),
                "expires_in": expires_in,
            }

            return Response(teacher_data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
##############################################################
###################     TEACHERS    PROFILE    ###############
##############################################################
class TeacherProfileAPIView(APIView):

    def get(self, request, *args, **kwargs):
        token_header = request.headers.get('Authorization', '')
        if not token_header or not token_header.startswith('Bearer '):
            return Response({"error": "Authorization token missing or invalid"}, status=status.HTTP_401_UNAUTHORIZED)

        token = token_header.split(' ')[1]

        try:
            decoded_token = jwt.decode(token, options={"verify_signature": False})
        except jwt.DecodeError:
            return Response({"error": "Failed to decode token"}, status=status.HTTP_401_UNAUTHORIZED)

   
        teacher_id = decoded_token.get('teacher_id')
      
        if not teacher_id:
            raise AuthenticationFailed('Student ID not found in token')


        try:
            teacher = Teacher.objects.get(id=teacher_id)
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher profile not found"}, status=404)
        teacher_datetime = teacher.teacher_date  # teacherning vaqt maydoni
        ashgabat_tz = pytz.timezone("Asia/Ashgabat") 
        if teacher_datetime:
            teacher_datetime = teacher_datetime.astimezone(ashgabat_tz)
            teacher_date = teacher_datetime.strftime('%Y-%m-%d')  # YYYY-MM-DD
            teacher_time = teacher_datetime.strftime('%H:%M:%S')  # HH:MM:SS
        else:
            teacher_date = None
            teacher_time = None
        data = {
                'full_name': teacher.full_name,
                'phone': teacher.user.phone if hasattr(teacher.user, 'phone') else None,
                'email': teacher.user.email if hasattr(teacher.user, 'email') else None,
                "telegram_id":teacher.user.telegram_id,
                'region': teacher.region,
                'districts': teacher.districts,
                'address': teacher.address,
                'brithday': teacher.brithday,
                'address': teacher.address,
                'document_type': teacher.document_type,
                'document': teacher.document,
                'teacher_date': teacher_date,  # YYYY-MM-DD (UTC+5)
                'teacher_time': teacher_time,  # HH:MM:SS (UTC+5)
        }

        return Response(data)
##############################################################
###################     STUNDENT    REGISTER   ###############
##############################################################
class RegisterStudentAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = StudentRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Telefon raqamga SMS kodi yuborildi. Kodni tasdiqlang."}, status=status.HTTP_200_OK)
        return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

##############################################################
###################     TEACHER     VERIFY SMS   #############
##############################################################

class TeacherVerifySmsCodeAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = TeacherVerifySmsCodeSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]

            try:
                teacher = Teacher.objects.get(user=user)
            except Teacher.DoesNotExist:
                return Response({"detail": "Teacher profile not found."}, status=status.HTTP_404_NOT_FOUND)


            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            access_token.set_exp(lifetime=timedelta(hours=13))
            access_token['teacher_id'] = teacher.id
            expires_in = timedelta(hours=13).total_seconds()

      

            return Response({
                "message": "Ro'yxatdan o'tish muvaffaqiyatli yakunlandi.",
                "login": serializer.validated_data['phone'],
                "password": serializer.validated_data['password'],
                "access_token": str(access_token),
                "expires_in": expires_in,
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

##############################################################
###################     STUNDENT    VERIFY SMS   #############
##############################################################
class StudentVerifySmsCodeAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = VerifySmsCodeSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data["user"]

            try:
                student = Student.objects.get(user=user)
            except Student.DoesNotExist:
                return Response({"detail": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            access_token.set_exp(lifetime=timedelta(hours=13))
            access_token['student_id'] = student.id
            expires_in = timedelta(hours=13).total_seconds()

            return Response({
                "message": "Ro'yxatdan o'tish muvaffaqiyatli yakunlandi.",
                "login": serializer.validated_data['phone'],
                "password": serializer.validated_data['password'],
                "access_token": str(access_token),
                "expires_in": expires_in,
                "role": user.role  # mana shu qator qo‘shildi
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



















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
class UserProfileAPIView(APIView):

    def get(self, request, *args, **kwargs):
        token_header = request.headers.get('Authorization', '')
        if not token_header or not token_header.startswith('Bearer '):
            return Response({"error": "Authorization token missing or invalid"}, status=status.HTTP_401_UNAUTHORIZED)

        token = token_header.split(' ')[1]

        try:
            decoded_token = jwt.decode(token, options={"verify_signature": False})
        except jwt.DecodeError:
            return Response({"error": "Failed to decode token"}, status=status.HTTP_401_UNAUTHORIZED)

        user_id = decoded_token.get('user_id')
        if not user_id:
            raise AuthenticationFailed('User ID not found in token')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        # Student profile
        if user.role == 'student':
            try:
                student = user.student_profile
            except Student.DoesNotExist:
                return Response({"error": "Student profile not found"}, status=404)

            student_datetime = student.student_date
            ashgabat_tz = pytz.timezone("Asia/Ashgabat")
            if student_datetime:
                student_datetime = student_datetime.astimezone(ashgabat_tz)
                student_date = student_datetime.strftime('%Y-%m-%d')
                student_time = student_datetime.strftime('%H:%M:%S')
            else:
                student_date = None
                student_time = None
            has_diagnost = Diagnost_Student.objects.filter(student=student).exists()
            data = {
            "id": student.id, 
            "identification": student.identification, 
            'full_name': student.full_name,
            'phone': getattr(student.user, 'phone', None),
            'email': getattr(student.user, 'email', None),
            "telegram_id":getattr(student.user, 'telegram_id', None),
            'region': student.region,
            'districts': student.districts,
            'address': student.address,
            'brithday': student.brithday,
            'academy_or_school': student.academy_or_school,
            'academy_or_school_name': student.academy_or_school_name,
            'class_name_uz': f"{student.class_name.classes.name}-sinf {student.class_name.name_uz}" if student.class_name else None,
            'class_name_ru': f"{student.class_name.classes.name}-класс {student.class_name.name_ru}" if student.class_name else None,
            'document_type': student.document_type,
            'document': student.document,
            'type_of_education': student.type_of_education,
            'student_date': student_date,
            'student_time': student_time,
            "has_diagnost": has_diagnost 
        }

        # Teacher profile
        elif user.role == 'teacher':
            try:
                teacher = user.teacher_profile
            except Teacher.DoesNotExist:
                return Response({"error": "Teacher profile not found"}, status=404)

            teacher_datetime = teacher.teacher_date
            ashgabat_tz = pytz.timezone("Asia/Ashgabat")
            if teacher_datetime:
                teacher_datetime = teacher_datetime.astimezone(ashgabat_tz)
                teacher_date = teacher_datetime.strftime('%Y-%m-%d')
                teacher_time = teacher_datetime.strftime('%H:%M:%S')
            else:
                teacher_date = None
                teacher_time = None

            data = {
                "role": "teacher",
                "id": teacher.id,
                "telegram_id":user.telegram_id,
                'full_name': teacher.full_name,
                'phone': user.phone,
                'email': user.email,
                'region': teacher.region,
                'districts': teacher.districts,
                'address': teacher.address,
                'brithday': teacher.brithday,
                'document_type': teacher.document_type,
                'document': teacher.document,
                'is_verified_teacher': teacher.is_verified_teacher,
                'teacher_date': teacher_date,
                'teacher_time': teacher_time,
            }

        else:
            return Response({"error": "Only student and teacher roles are supported"}, status=403)

        return Response(data)
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

        user_id = decoded_token.get('user_id')
        if not user_id:
            raise AuthenticationFailed('User ID not found in token')

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        if user.role == 'student':
            try:
                student = user.student_profile
            except Student.DoesNotExist:
                return Response({"error": "Student profile not found"}, status=404)

            student_datetime = student.student_date
            ashgabat_tz = pytz.timezone("Asia/Ashgabat")
            if student_datetime:
                student_datetime = student_datetime.astimezone(ashgabat_tz)
                student_date = student_datetime.strftime('%Y-%m-%d')
                student_time = student_datetime.strftime('%H:%M:%S')
            else:
                student_date = None
                student_time = None

            has_diagnost = Diagnost_Student.objects.filter(student=student).exists()

            data = {
                "id": student.id,
                "identification": student.identification,
                'full_name': student.full_name,
                'phone': getattr(student.user, 'phone', None),
                'email': getattr(student.user, 'email', None),
                "telegram_id": getattr(student.user, 'telegram_id', None),
                'region': student.region,
                'districts': student.districts,
                'address': student.address,
                'brithday': student.brithday,
                'academy_or_school': student.academy_or_school,
                'academy_or_school_name': student.academy_or_school_name,
                'class_name_uz': f"{student.class_name.classes.name}-sinf {student.class_name.name_uz}" if student.class_name else None,
                'class_name_ru': f"{student.class_name.classes.name}-класс {student.class_name.name_ru}" if student.class_name else None,
                'document_type': student.document_type,
                'document': student.document,
                'type_of_education': student.type_of_education,
                'student_date': student_date,
                'student_time': student_time,
                "role": "student",
                "has_diagnost": has_diagnost
            }

        elif user.role == 'teacher':
            try:
                teacher = user.teacher_profile
            except Teacher.DoesNotExist:
                return Response({"error": "Teacher profile not found"}, status=404)

            teacher_datetime = teacher.teacher_date
            ashgabat_tz = pytz.timezone("Asia/Ashgabat")
            if teacher_datetime:
                teacher_datetime = teacher_datetime.astimezone(ashgabat_tz)
                teacher_date = teacher_datetime.strftime('%Y-%m-%d')
                teacher_time = teacher_datetime.strftime('%H:%M:%S')
            else:
                teacher_date = None
                teacher_time = None

            data = {
                "role": "teacher",
                "id": teacher.id,
                'full_name': teacher.full_name,
                'phone': user.phone,
                'email': user.email,
                "telegram_id":user.telegram_id,
                'region': teacher.region,
                'districts': teacher.districts,
                'address': teacher.address,
                'brithday': teacher.brithday,
                'document_type': teacher.document_type,
                'document': teacher.document,
                'is_verified_teacher': teacher.is_verified_teacher,
                'teacher_date': teacher_date,
                'teacher_time': teacher_time,
            }

        elif user.role == 'admin':
            data = {
                "role": "admin",
                "id": user.id,
                "full_name": f"{user.first_name} {user.last_name}",
                "phone": user.phone,
                "email": user.email,
            }

        else:
            return Response({"error": "Only student, teacher, and admin roles are supported"}, status=403)

        return Response(data)

class UpdateStudentFieldAPIView(APIView):
    def post(self, request, *args, **kwargs):
        student_id = request.data.get('student_id')
        if not student_id:
            return Response({"error": "student_id is required"}, status=400)

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        # Telefon, email, class_name ni o‘zgartirish mumkin emas
        protected_fields = ['phone', 'email', 'class_name']

        for field, value in request.data.items():
            if field == 'student_id':
                continue
            if field in protected_fields:
                return Response({"error": f"Field '{field}' cannot be updated"}, status=403)
            if hasattr(student, field):
                setattr(student, field, value)

        student.save()
        return Response({"message": "Field(s) updated successfully"})
from django.utils.timezone import localtime
import pytz
from rest_framework.permissions import IsAuthenticated
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.utils.encoding import escape_uri_path
from openpyxl import Workbook


class StudentsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ashgabat_tz = pytz.timezone("Asia/Ashgabat")
        export_excel = request.GET.get("export") == "excel"

        students = Student.objects.filter(user__role='student', status=True).order_by('id')

        data_json = []  # JSON uchun
        data_excel = []  # Excel uchun

        for student in students:
            student_datetime = student.student_date
            if student_datetime:
                student_datetime = student_datetime.astimezone(ashgabat_tz)
                student_date = student_datetime.strftime('%Y-%m-%d')
                student_time = student_datetime.strftime('%H:%M:%S')
            else:
                student_date = None
                student_time = None

            last_login_obj = StudentLoginHistory.objects.filter(student=student).order_by('-login_time').first()
            if last_login_obj:
                last_login_local = last_login_obj.login_time.astimezone(ashgabat_tz)
                last_login_formatted = last_login_local.strftime('%d/%m/%Y %H:%M')
            else:
                last_login_formatted = None

            # JSON uchun ingliz tilidagi maydonlar
            data_json.append({
                "id": student.id,
                "full_name": student.full_name,
                "phone": student.user.phone,
                "email": student.user.email,
                "region": student.region,
                "districts": student.districts,
                "address": student.address,
                "brithday": student.brithday,
                "academy_or_school": student.academy_or_school,
                "academy_or_school_name": student.academy_or_school_name,
                "class_name_uz": f"{student.class_name.classes.name}-sinf {student.class_name.name_uz}" if student.class_name else None,
                "class_name_ru": f"{student.class_name.classes.name}-класс {student.class_name.name_ru}" if student.class_name else None,
                "document_type": student.document_type,
                "document": student.document,
                "type_of_education": student.type_of_education,
                "student_date": student_date,
                "student_time": student_time,
                "last_login_time": last_login_formatted
            })

            # Excel uchun o‘zbek tilidagi maydonlar
            data_excel.append({
                "ID": student.id,
                "F.I.Sh.": student.full_name,
                "Telefon": student.user.phone,
                "Email": student.user.email,
                "Viloyat": student.region,
                "Tuman": student.districts,
                "Manzil": student.address,
                "Tug‘ilgan sana": student.brithday,
                "Ta'lim muassasasi": student.academy_or_school,
                "Muassasa nomi": student.academy_or_school_name,
                "Sinf (UZ)": f"{student.class_name.classes.name}-sinf {student.class_name.name_uz}" if student.class_name else None,
                "Sinf (RU)": f"{student.class_name.classes.name}-класс {student.class_name.name_ru}" if student.class_name else None,
                "Hujjat turi": student.document_type,
                "Hujjat raqami": student.document,
                "Ta'lim turi": student.type_of_education,
                "Ro‘yxatga olingan sana": student_date,
                "Ro‘yxatga olingan vaqt": student_time,
                "Oxirgi tizimga kirgan vaqt": last_login_formatted
            })

        if export_excel:
            wb = Workbook()
            ws = wb.active
            ws.title = "O'quvchilar ro'yxati"

            headers = list(data_excel[0].keys()) if data_excel else []
            ws.append(headers)

            for row in data_excel:
                ws.append(list(row.values()))

            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            filename = escape_uri_path("Oquvchilar_royxati.xlsx")
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            wb.save(response)
            return response

        # JSON qaytarish (paginatsiya bilan)
        page = int(request.GET.get('page', 1))
        size = int(request.GET.get('size', 10))

        paginator = Paginator(data_json, size)
        total_count = paginator.count
        total_pages = paginator.num_pages

        try:
            current_page = paginator.page(page)
        except EmptyPage:
            return Response({
                "error": "Page not found",
                "page": page,
                "size": size,
                "total": total_count,
                "total_pages": total_pages,
                "results": []
            }, status=404)

        return Response({
            "page": page,
            "size": size,
            "total": total_count,
            "total_pages": total_pages,
            "results": current_page.object_list
        })







from user_agents import parse
from django.contrib.sessions.models import Session
from django.db import transaction
import user_agents 



class LoginAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            # Tokenlarni yaratish
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            access_token.set_exp(lifetime=timedelta(hours=13))
            expires_in = timedelta(hours=13).total_seconds()

            profile_data = {}

            if user.role == 'student':
                try:
                    student = Student.objects.get(user=user)
                    StudentLoginHistory.objects.create(student=student)

                    access_token['student_id'] = student.id
                    profile_data = {
                        "id": student.id,
                        "full_name": student.full_name,
                        "phone": user.phone,
                        "role": user.role,
                        "status": student.status,
                        "access_token": str(access_token),
                        "refresh_token": str(refresh),
                        "expires_in": expires_in,
                    }
                except Student.DoesNotExist:
                    return Response({"detail": "Student profile not found."}, status=status.HTTP_404_NOT_FOUND)

            elif user.role == 'teacher':
                try:
                    teacher = Teacher.objects.get(user=user)
                    access_token['teacher_id'] = teacher.id
                    profile_data = {
                        "id": teacher.id,
                        "full_name": teacher.full_name,
                        "phone": user.phone,
                        "role": user.role,
                        "status": teacher.status,
                        "access_token": str(access_token),
                        "refresh_token": str(refresh),
                        "expires_in": expires_in,
                    }
                except Teacher.DoesNotExist:
                    return Response({"detail": "Teacher profile not found."}, status=status.HTTP_404_NOT_FOUND)

            elif user.role == 'admin':
                # Admin uchun oddiy profil javobi
                profile_data = {
                    "id": user.id,
                    "full_name": f"{user.first_name} {user.last_name}".strip(),
                    "phone": user.phone,
                    "role": user.role,
                    "access_token": str(access_token),
                    "refresh_token": str(refresh),
                    "expires_in": expires_in,
                }

            else:
                return Response({"detail": "Role is not supported."}, status=status.HTTP_403_FORBIDDEN)

            return Response(profile_data, status=status.HTTP_200_OK)

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
        




class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            student = Student.objects.get(user=user)
            latest_login = StudentLoginHistory.objects.filter(student=student, logout_time__isnull=True).last()
            if latest_login:
                latest_login.logout_time = timezone.now()
                latest_login.save()
        except Student.DoesNotExist:
            pass  # Teacher uchun yozmaslik mumkin

        # Tokenni blacklist qilish yoki frontend tokenni o‘chirish logikasi shu yerda bo‘lishi mumkin
        return Response({"detail": "Chiqqan vaqtingiz yozildi."}, status=200)



class TelegramIDCheckAPIView(APIView):
    def post(self, request):
        telegram_id = request.data.get('telegram_id')

        if not telegram_id:
            return Response({"detail": "telegram_id yuborilishi shart."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(telegram_id=telegram_id)
        except User.DoesNotExist:
            return Response({"detail": "Bunday telegram_id bilan foydalanuvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        if user.role == 'teacher':
            try:
                teacher = user.teacher_profile
                serializer = TeacherSerializer(teacher)
                return Response({"role": "teacher", "data": serializer.data})
            except Teacher.DoesNotExist:
                return Response({"detail": "O‘qituvchi profili topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        elif user.role == 'student':
            try:
                student = user.student_profile
                serializer = StudentSerializer(student)
                return Response({"role": "student", "data": serializer.data})
            except Student.DoesNotExist:
                return Response({"detail": "O‘quvchi profili topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"detail": "Bunday rol aniqlanmadi."}, status=status.HTTP_400_BAD_REQUEST)