from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
import random
from django_app.app_user.models import User, UserSMSAttempt
from django_app.app_user.sms_service import send_sms


class VerifyPhoneChangeView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Yangi telefon raqamini tasdiqlash
        """
        user = request.user
        sms_code = request.data.get('sms_code')
        new_phone = request.data.get('new_phone')
        
        if not sms_code or not new_phone:
            return Response(
                {"error": "SMS kod va yangi telefon raqamini kiriting."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # SMS kodni tekshirish
        if not user.sms_code or user.sms_code != sms_code:
            return Response(
                {"error": "Noto'g'ri SMS kod yoki kod muddati tugagan."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Yangi telefon raqami allaqachon mavjudligini tekshirish
        if User.objects.filter(phone=new_phone).exclude(id=user.id).exists():
            return Response(
                {"error": "Bu telefon raqami allaqachon ro'yxatdan o'tgan."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Telefon raqamini yangilash
        old_phone = user.phone
        user.phone = new_phone
        user.sms_code = None  # SMS kodni tozalash
        user.save()
        
        # SMS yuborishni registratsiya qilish
        UserSMSAttempt.register_attempt(user)
        
        # Yangi telefon raqamiga tasdiqlash SMSi yuborish (ixtiyoriy)
        confirmation_sms_code = str(random.randint(10000, 99999))
        user.sms_code = confirmation_sms_code
        user.save()
        
        send_sms(new_phone, f"Telefon raqamingiz muvaffaqiyatli yangilandi. Yangi raqam: {new_phone}")
        
        return Response({
            "message": "Telefon raqami muvaffaqiyatli yangilandi.",
            "new_phone": new_phone,
            "old_phone": old_phone
        }, status=status.HTTP_200_OK)


class UniversalUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Foydalanuvchi ma'lumotlarini yangilash.
        Agar telefon raqami o'zgartirilsa, parol tekshiriladi va SMS yuboriladi.
        """
        user = request.user
        data = request.data.copy()
        
        # Yangi telefon raqami kiritilganligini tekshirish
        new_phone = data.get('phone')
        current_phone = user.phone
        
        # Agar telefon raqami o'zgartirilayotgan bo'lsa
        if new_phone and new_phone != current_phone:
            # Parolni tekshirish
            password = data.get('password')
            if not password:
                return Response(
                    {"error": "Telefon raqamini o'zgartirish uchun parolni kiriting."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parolni tekshirish
            auth_user = authenticate(phone=current_phone, password=password)
            if not auth_user:
                return Response(
                    {"error": "Noto'g'ri parol."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Yangi telefon raqami allaqachon mavjudligini tekshirish
            if User.objects.filter(phone=new_phone).exists():
                return Response(
                    {"error": "Bu telefon raqami allaqachon ro'yxatdan o'tgan."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # SMS yuborish imkoniyatini tekshirish
            can_send, remaining_time = UserSMSAttempt.can_send_sms(user)
            if not can_send:
                remaining_time_str = str(remaining_time).split(".")[0]
                return Response({
                    "error": f"SMS yuborish imkoniyati cheklangan. {remaining_time_str} sonra urinib ko'ring.",
                    "retry_after": remaining_time_str
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # SMS kod yaratish va yuborish
            sms_code = str(random.randint(10000, 99999))
            user.sms_code = sms_code
            user.save()
            
            # SMS yuborish
            sms_sent = send_sms(new_phone, sms_code)
            
            if not sms_sent:
                return Response({
                    "error": "SMS yuborishda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # SMS yuborishni registratsiya qilish
            UserSMSAttempt.register_attempt(user)
            
            return Response({
                "message": "Telefon raqami yangilandi. SMS kod yangi raqamga yuborildi.",
                "sms_sent": True,
                "new_phone": new_phone,
                "next_step": "verify_phone_change"
            }, status=status.HTTP_200_OK)
        
        # Agar telefon raqami o'zgartirilmasa, oddiy update
        return self.update_user_profile(user, data)
    
    def update_user_profile(self, user, data):
        """
        Foydalanuvchi profilini yangilash (telefon raqamisiz)
        """
        try:
            # User modelidagi maydonlarni yangilash
            user_fields = ['first_name', 'last_name', 'email']
            for field in user_fields:
                if field in data and data[field] is not None:
                    setattr(user, field, data[field])
            
            user.save()
            
            # Role bo'yicha profilni yangilash
            profile_data = self.prepare_profile_data(user.role, data)
            self.update_role_profile(user, profile_data)
            
            return Response({
                "message": "Ma'lumotlar muvaffaqiyatli yangilandi.",
                "user": {
                    "phone": user.phone,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"Ma'lumotlarni yangilashda xatolik: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def prepare_profile_data(self, role, data):
        """
        Role bo'yicha profil ma'lumotlarini tayyorlash
        """
        profile_fields_map = {
            'tutor': ['full_name', 'region', 'districts', 'address'],
            'teacher': ['full_name', 'region', 'districts', 'address', 'brithday', 
                       'document_type', 'document', 'is_verified_teacher'],
            'student': ['full_name', 'region', 'districts', 'address', 'brithday',
                       'academy_or_school', 'academy_or_school_name', 'class_name',
                       'document_type', 'document', 'type_of_education'],
            'parent': ['full_name', 'region', 'districts', 'address']
        }
        
        profile_data = {}
        fields = profile_fields_map.get(role, [])
        for field in fields:
            if field in data and data[field] is not None:
                profile_data[field] = data[field]
        
        return profile_data
    
    def update_role_profile(self, user, profile_data):
        """
        Role profilini yangilash
        """
        if not profile_data:
            return
            
        try:
            if user.role == 'tutor' and hasattr(user, 'tutor_profile'):
                for field, value in profile_data.items():
                    setattr(user.tutor_profile, field, value)
                user.tutor_profile.save()
            
            elif user.role == 'teacher' and hasattr(user, 'teacher_profile'):
                for field, value in profile_data.items():
                    setattr(user.teacher_profile, field, value)
                user.teacher_profile.save()
            
            elif user.role == 'student' and hasattr(user, 'student_profile'):
                for field, value in profile_data.items():
                    setattr(user.student_profile, field, value)
                user.student_profile.save()
            
            elif user.role == 'parent' and hasattr(user, 'parent_profile'):
                for field, value in profile_data.items():
                    setattr(user.parent_profile, field, value)
                user.parent_profile.save()
                
        except Exception as e:
            raise Exception(f"Profil yangilashda xatolik: {str(e)}")
        

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Parolni yangilash
        """
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response(
                {"error": "Eski va yangi parolni kiriting."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Eski parolni tekshirish
        auth_user = authenticate(phone=user.phone, password=old_password)
        if not auth_user:
            return Response(
                {"error": "Eski parol noto'g'ri."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Yangi parolni o'rnatish
        user.set_password(new_password)
        user.save()
        
        return Response({
            "message": "Parol muvaffaqiyatli yangilandi."
        }, status=status.HTTP_200_OK)