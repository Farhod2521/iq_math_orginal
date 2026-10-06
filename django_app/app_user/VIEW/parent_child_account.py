"""
Telefonsiz farzand hisobi (bir oilada bitta telefon bo'lgan holat uchun).

Oqim:
  1. Ota-ona farzand uchun telefonsiz o'quvchi hisobini yaratadi (ism + sinf).
     Farzand hisobiga telefon o'rniga ichki login yoziladi ("c" + raqamlar) — u bilan kirib bo'lmaydi.
  2. Ota-ona "Farzand sifatida kirish" bilan farzand profiliga o'tadi
     (token ichida `acting_parent` — qaysi ota-ona o'tkazgani).
  3. Farzand profilidan "Ota-ona hisobiga qaytish" — `acting_parent` bo'yicha ota-ona tokeni beriladi.
  4. Keyinchalik farzandga telefon olinsa, ota-ona hisobga haqiqiy raqam biriktiradi.

Endpointlar (/api/v1/auth/ ostida):
  POST parent/children/create/                 {full_name, class_name}
  POST parent/children/<id>/switch/            {device_id?, user_agent?, replace_device_id?}
  POST child/return-to-parent/
  POST parent/children/<id>/set-phone/         {phone}
"""
import random
import string
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from django_app.app_user.models import (
    Parent, ParentLoginHistory, ParentStudentRelation, Student, StudentLoginHistory, Subject, User,
)

VIRTUAL_PHONE_PREFIX = "c"
ACTING_PARENT_CLAIM = "acting_parent"
ACCESS_LIFETIME = timedelta(minutes=30)


def is_virtual_phone(phone):
    """Telefonsiz farzand hisobining ichki logini (haqiqiy telefon emas)."""
    return bool(phone) and str(phone).startswith(VIRTUAL_PHONE_PREFIX)


def _new_virtual_phone():
    while True:
        candidate = VIRTUAL_PHONE_PREFIX + "".join(random.choices(string.digits, k=12))
        if not User.objects.filter(phone=candidate).exists():
            return candidate


def _parent_of(request):
    parent = getattr(request.user, "parent_profile", None)
    if request.user.role != "parent" or parent is None:
        return None
    return parent


def _child_relation(parent, student_id):
    return (
        ParentStudentRelation.objects.filter(parent=parent, student_id=student_id, is_confirmed=True)
        .select_related("student__user")
        .first()
    )


def _issue_tokens(user, device=None, extra_claims=None):
    from django_app.app_user.device_service import attach_device_claim

    refresh = RefreshToken.for_user(user)
    for key, value in (extra_claims or {}).items():
        # refresh'ga yozilgan claim yangilangan access tokenlarga ham o'tadi
        refresh[key] = value
    access = refresh.access_token
    access.set_exp(lifetime=ACCESS_LIFETIME)
    attach_device_claim(refresh, access, device)
    return refresh, access


class ParentCreateChildAPIView(APIView):
    """Ota-ona farzandi uchun telefonsiz o'quvchi hisobini yaratadi."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        parent = _parent_of(request)
        if parent is None:
            return Response({"detail": "Faqat ota-onalar uchun."}, status=status.HTTP_403_FORBIDDEN)

        full_name = str(request.data.get("full_name") or "").strip()
        class_id = request.data.get("class_name")
        if len(full_name) < 3:
            return Response({"detail": "Farzandning ism-familiyasini kiriting."}, status=status.HTTP_400_BAD_REQUEST)
        class_name = Subject.objects.filter(id=class_id).first() if class_id else None
        if class_name is None:
            return Response({"detail": "Sinfni tanlang."}, status=status.HTTP_400_BAD_REQUEST)

        from django_app.app_payments.models import Subscription, SubscriptionSetting

        with transaction.atomic():
            user = User(phone=_new_virtual_phone(), role="student")
            user.set_unusable_password()
            user.save()
            student = Student.objects.create(
                user=user,
                full_name=full_name[:200],
                class_name=class_name,
                status=True,
                lang=parent.lang or "uz",
                student_date=timezone.now(),
            )
            setting = SubscriptionSetting.objects.first()
            free_days = setting.free_trial_days if setting else 7
            Subscription.objects.create(
                student=student,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=free_days),
                is_paid=False,
            )
            ParentStudentRelation.objects.create(parent=parent, student=student, is_confirmed=True)

        return Response({
            "id": student.id,
            "full_name": student.full_name,
            "identification": student.identification,
            "has_phone": False,
        }, status=status.HTTP_201_CREATED)


class ParentSwitchToChildAPIView(APIView):
    """Ota-ona farzand profiliga o'tadi: farzand uchun token qaytariladi (login javobi bilan bir xil)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, student_id):
        parent = _parent_of(request)
        if parent is None:
            return Response({"detail": "Faqat ota-onalar uchun."}, status=status.HTTP_403_FORBIDDEN)
        relation = _child_relation(parent, student_id)
        if relation is None:
            return Response({"detail": "Farzand topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        student = relation.student
        child_user = student.user
        if not child_user.is_active:
            return Response({"detail": "Farzand hisobi bloklangan."}, status=status.HTTP_403_FORBIDDEN)

        # Qurilma cheklovi farzand hisobiga ham amal qiladi
        from django_app.app_user.device_service import (
            DeviceLimitReached, device_limit_response_data, register_login,
        )
        try:
            device = register_login(child_user, request, request.data.get("replace_device_id"))
        except DeviceLimitReached as exc:
            return Response(device_limit_response_data(exc.devices), status=status.HTTP_409_CONFLICT)

        refresh, access = _issue_tokens(child_user, device, {ACTING_PARENT_CLAIM: parent.user_id})
        access["student_id"] = student.id
        StudentLoginHistory.objects.create(student=student)
        from django_app.app_student.achievements import check_achievements_safe
        check_achievements_safe(student)

        return Response({
            "id": student.id,
            "full_name": student.full_name,
            "phone": None if is_virtual_phone(child_user.phone) else child_user.phone,
            "role": "student",
            "status": student.status,
            "access_token": str(access),
            "refresh_token": str(refresh),
            "expires_in": ACCESS_LIFETIME.total_seconds(),
            "acting_parent": {"id": parent.id, "full_name": parent.full_name, "phone": parent.user.phone},
        })


class ReturnToParentAPIView(APIView):
    """Farzand profilidan ota-ona hisobiga qaytish (faqat ota-ona o'tkazgan sessiyada)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.auth
        parent_user_id = token.get(ACTING_PARENT_CLAIM) if token is not None else None
        student = getattr(request.user, "student_profile", None)
        if not parent_user_id or student is None:
            return Response({"detail": "Bu sessiya ota-ona orqali ochilmagan."}, status=status.HTTP_403_FORBIDDEN)

        parent = Parent.objects.filter(user_id=parent_user_id).select_related("user").first()
        if parent is None or not parent.user.is_active or _child_relation(parent, student.id) is None:
            return Response({"detail": "Ota-ona hisobi topilmadi."}, status=status.HTTP_403_FORBIDDEN)

        refresh, access = _issue_tokens(parent.user)
        access["parent_id"] = parent.id
        ParentLoginHistory.objects.create(parent=parent)
        return Response({
            "id": parent.id,
            "full_name": parent.full_name,
            "phone": parent.user.phone,
            "role": "parent",
            "access_token": str(access),
            "refresh_token": str(refresh),
            "expires_in": ACCESS_LIFETIME.total_seconds(),
        })


class ParentChildSetPhoneAPIView(APIView):
    """Telefonsiz farzand hisobiga haqiqiy telefon raqam biriktirish (farzand endi o'zi kira oladi)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, student_id):
        parent = _parent_of(request)
        if parent is None:
            return Response({"detail": "Faqat ota-onalar uchun."}, status=status.HTTP_403_FORBIDDEN)
        relation = _child_relation(parent, student_id)
        if relation is None:
            return Response({"detail": "Farzand topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        child_user = relation.student.user
        if not is_virtual_phone(child_user.phone):
            return Response({"detail": "Bu hisobda telefon raqam allaqachon bor."}, status=status.HTTP_400_BAD_REQUEST)

        digits = "".join(ch for ch in str(request.data.get("phone") or "") if ch.isdigit())
        if len(digits) == 9:
            digits = "998" + digits
        if len(digits) != 12 or not digits.startswith("998"):
            return Response({"detail": "Telefon raqamni to'g'ri kiriting."}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(phone=digits).exists():
            return Response({"detail": "Bu telefon raqam allaqachon ro'yxatdan o'tgan."}, status=status.HTTP_400_BAD_REQUEST)

        password = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        child_user.phone = digits
        child_user.set_password(password)
        child_user.save()
        return Response({"login": digits, "password": password, "has_phone": True})
