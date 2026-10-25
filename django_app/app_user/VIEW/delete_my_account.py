"""
Foydalanuvchi o'z akkauntini to'liq o'chirishi (o'quvchi, ota-ona, o'qituvchi).

DELETE /api/v1/auth/delete-account/
  body: {"password": "..."}      — paroli bor akkauntlar uchun majburiy
        {"confirm": true}        — paroli yo'q (SMS orqali kiradigan) akkauntlar uchun

Ota-ona o'chirilsa, u yaratgan (telefon raqamisiz) farzand akkauntlari ham o'chadi —
ular ota-onasiz ochib bo'lmaydigan akkauntlar. Telefon raqami bilan alohida ro'yxatdan
o'tgan farzandlar o'chmaydi, faqat bog'lanish uziladi.
"""
from django.db import transaction
from django.db.models import ProtectedError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_student.models import TopicHelpRequestIndependent
from django_app.app_user.models import User
from django_app.app_user.VIEW.parent_child_account import VIRTUAL_PHONE_PREFIX

ALLOWED_ROLES = ("student", "parent", "tutor")


def _blocked_reason(user):
    if user.role not in ALLOWED_ROLES:
        return "Bu turdagi akkauntni o'zingiz o'chira olmaysiz. Administratorga murojaat qiling."
    # Ota-ona yaratgan farzand akkauntini faqat ota-ona boshqaradi
    if str(user.phone or "").startswith(VIRTUAL_PHONE_PREFIX):
        return "Bu akkauntni faqat ota-onangiz o'chira oladi."
    return None


class DeleteMyAccountAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """O'chirish oynasi uchun: parol so'raladimi va o'chirish mumkinmi."""
        reason = _blocked_reason(request.user)
        return Response({
            "can_delete": reason is None,
            "reason": reason,
            "requires_password": request.user.has_usable_password(),
        })

    def delete(self, request):
        user = request.user

        reason = _blocked_reason(user)
        if reason:
            return Response({"detail": reason}, status=status.HTTP_403_FORBIDDEN)

        if user.has_usable_password():
            password = request.data.get("password")
            if not password:
                return Response(
                    {"detail": "Akkauntni o'chirish uchun parolni kiriting."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not user.check_password(password):
                return Response({"detail": "Parol noto'g'ri kiritilgan."}, status=status.HTTP_400_BAD_REQUEST)
        elif request.data.get("confirm") is not True:
            return Response({"detail": "O'chirishni tasdiqlang."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                if user.role == "parent":
                    parent = getattr(user, "parent_profile", None)
                    if parent is not None:
                        User.objects.filter(
                            role="student",
                            phone__startswith=VIRTUAL_PHONE_PREFIX,
                            student_profile__parent_relations__parent=parent,
                        ).delete()

                teacher = getattr(user, "teacher_profile", None)
                if teacher is not None:
                    TopicHelpRequestIndependent.objects.filter(teacher=teacher).update(teacher=None)

                user.delete()  # CASCADE → profil va unga bog'liq ma'lumotlar ham o'chadi
        except ProtectedError:
            return Response(
                {"detail": "Akkauntni hozircha o'chirib bo'lmadi. Administratorga murojaat qiling."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"detail": "Akkauntingiz to'liq o'chirildi."}, status=status.HTTP_200_OK)
