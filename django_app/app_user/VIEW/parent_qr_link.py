"""
Ota-onani QR kod orqali farzandga biriktirish.

Oqim:
  1. O'quvchi "Ota-ona uchun" sahifasini ochadi — QR kod ichida imzolangan token
     (farzand id si) bo'ladi: https://iqmath.uz/parent-connect?t=<token>
  2. Ota-ona QR ni skanerlaydi, telefon raqamini kiritadi (check-phone).
     - Ota-ona sifatida ro'yxatdan o'tgan bo'lsa: parol kiritadi (login) — farzand biriktiriladi.
     - Ro'yxatdan o'tmagan bo'lsa: ism-familiya kiritadi (register) -> SMS kod (register/verify)
       -> parol qo'yadi (register/complete) -> login. Farzand avtomatik biriktiriladi.

Endpointlar (/api/v1/auth/ ostida):
  GET  student/parent-qr/                      (o'quvchi tokeni bilan) -> {token, student}
  POST parent-qr/info/                         {token}
  POST parent-qr/check-phone/                  {token, phone}
  POST parent-qr/login/                        {token, phone, password, device_id?, user_agent?}
  POST parent-qr/register/                     {token, phone, full_name}
  POST parent-qr/register/verify/              {token, phone, code}
  POST parent-qr/register/complete/            {token, phone, code, password}
"""
import random

from django.core import signing
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_user.models import Parent, ParentLoginHistory, ParentStudentRelation, Student, User
from django_app.app_user.VIEW.parent_child_account import (
    ACCESS_LIFETIME, _issue_tokens, _normalize_phone,
)

QR_SALT = "parent-qr-link"
QR_MAX_AGE = 60 * 60 * 24  # QR 1 kun amal qiladi (sahifa har ochilganda yangilanadi)

_REG_KEY = "parent-qr-reg:{}"
_REG_TTL = 600  # 10 daqiqa
_REG_MAX_TRIES = 5
_REG_RESEND_SECONDS = 120
_MIN_PASSWORD = 6


def make_qr_token(student):
    return signing.dumps({"s": student.id}, salt=QR_SALT, compress=True)


def _student_from_token(token):
    try:
        payload = signing.loads(str(token or ""), salt=QR_SALT, max_age=QR_MAX_AGE)
    except signing.SignatureExpired:
        return None, "QR kod muddati tugagan. Farzandingizdan yangi QR kodni so'rang."
    except signing.BadSignature:
        return None, "QR kod noto'g'ri."
    student = Student.objects.filter(id=payload.get("s")).select_related("user", "class_name").first()
    if student is None or not student.user.is_active:
        return None, "Farzand hisobi topilmadi."
    return student, None


def _student_data(student):
    return {
        "id": student.id,
        "full_name": student.full_name,
        "identification": student.identification,
        "class_name": student.class_name.name if student.class_name else None,
    }


def _resolve(request):
    """token va telefonni tekshiradi: (student, phone, error_response)"""
    student, error = _student_from_token(request.data.get("token"))
    if error:
        return None, None, Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
    phone = _normalize_phone(request.data.get("phone"))
    if phone is None:
        return None, None, Response({"detail": "Telefon raqamni to'g'ri kiriting."}, status=status.HTTP_400_BAD_REQUEST)
    if student.user.phone == phone:
        return None, None, Response(
            {"detail": "Bu farzandning o'z raqami. Ota-ona raqamini kiriting."}, status=status.HTTP_400_BAD_REQUEST
        )
    return student, phone, None


def _link(parent, student):
    relation, created = ParentStudentRelation.objects.get_or_create(
        parent=parent, student=student, defaults={"is_confirmed": True}
    )
    if not created and not relation.is_confirmed:
        relation.is_confirmed = True
        relation.save(update_fields=["is_confirmed"])


class StudentParentQrAPIView(APIView):
    """O'quvchi uchun QR token (ota-ona skanerlaydi)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = getattr(request.user, "student_profile", None)
        if request.user.role != "student" or student is None:
            return Response({"detail": "Faqat o'quvchilar uchun."}, status=status.HTTP_403_FORBIDDEN)
        parents = (
            ParentStudentRelation.objects.filter(student=student, is_confirmed=True)
            .select_related("parent__user")
        )
        return Response({
            "token": make_qr_token(student),
            "expires_in": QR_MAX_AGE,
            "student": _student_data(student),
            "parents": [
                {"id": rel.parent.id, "full_name": rel.parent.full_name, "phone": rel.parent.user.phone}
                for rel in parents
            ],
        })


class ParentQrInfoAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        student, error = _student_from_token(request.data.get("token"))
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"student": _student_data(student)})


class ParentQrCheckPhoneAPIView(APIView):
    """Telefon bo'yicha: ota-ona ro'yxatdan o'tganmi (parol so'raladi) yoki yo'q (ro'yxatdan o'tadi)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        student, phone, error = _resolve(request)
        if error:
            return error
        user = User.objects.filter(phone=phone).first()
        if user is None:
            return Response({"exists": False, "linked": False, "phone": phone})
        parent = getattr(user, "parent_profile", None)
        if user.role != "parent" or parent is None:
            return Response(
                {"detail": "Bu raqam boshqa turdagi hisob bilan ro'yxatdan o'tgan. Boshqa raqam kiriting."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.is_blocked or not user.is_active:
            return Response({"detail": "Hisob bloklangan."}, status=status.HTTP_403_FORBIDDEN)
        linked = ParentStudentRelation.objects.filter(parent=parent, student=student, is_confirmed=True).exists()
        return Response({"exists": True, "linked": linked, "phone": phone, "full_name": parent.full_name})


class ParentQrLoginAPIView(APIView):
    """Ota-ona parol bilan kiradi va farzand hisobiga biriktiriladi (login javobi bilan bir xil)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        from django_app.app_user.serializers import LoginSerializer

        student, phone, error = _resolve(request)
        if error:
            return error
        serializer = LoginSerializer(data={"phone": phone, "password": request.data.get("password") or ""})
        if not serializer.is_valid():
            errors = serializer.errors.get("non_field_errors") or ["Telefon raqam yoki parol noto'g'ri."]
            return Response({"detail": errors[0]}, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.validated_data["user"]
        parent = getattr(user, "parent_profile", None)
        if user.role != "parent" or parent is None:
            return Response({"detail": "Bu hisob ota-ona hisobi emas."}, status=status.HTTP_400_BAD_REQUEST)

        from django_app.app_user.device_service import (
            DeviceLimitReached, device_limit_response_data, register_login,
        )
        try:
            device = register_login(user, request, request.data.get("replace_device_id"))
        except DeviceLimitReached as exc:
            return Response(device_limit_response_data(exc.devices), status=status.HTTP_409_CONFLICT)

        _link(parent, student)
        refresh, access = _issue_tokens(user, device)
        access["parent_id"] = parent.id
        ParentLoginHistory.objects.create(parent=parent)
        return Response({
            "id": parent.id,
            "full_name": parent.full_name,
            "phone": user.phone,
            "role": "parent",
            "access_token": str(access),
            "refresh_token": str(refresh),
            "expires_in": ACCESS_LIFETIME.total_seconds(),
            "child": _student_data(student),
        })


class ParentQrRegisterAPIView(APIView):
    """Yangi ota-ona: ism-familiya + telefon -> SMS kod."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        student, phone, error = _resolve(request)
        if error:
            return error
        full_name = str(request.data.get("full_name") or "").strip()
        if len(full_name) < 3:
            return Response({"detail": "Ism-familiyangizni kiriting."}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(phone=phone).exists():
            return Response({"detail": "Bu telefon raqam allaqachon ro'yxatdan o'tgan."}, status=status.HTTP_400_BAD_REQUEST)

        key = _REG_KEY.format(phone)
        previous = cache.get(key)
        now_ts = timezone.now().timestamp()
        if previous and now_ts - previous.get("sent_at", 0) < _REG_RESEND_SECONDS:
            retry_after = int(_REG_RESEND_SECONDS - (now_ts - previous["sent_at"])) + 1
            return Response(
                {"detail": f"Kodni qayta olish uchun {retry_after} soniya kuting.", "retry_after": retry_after},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        from django_app.app_user.sms_service import send_sms

        code = str(random.randint(10000, 99999))
        cache.set(key, {
            "full_name": full_name[:200],
            "student_id": student.id,
            "lang": str(request.data.get("lang") or "uz")[:10],
            "code": code,
            "tries": 0,
            "verified": False,
            "sent_at": now_ts,
        }, _REG_TTL)
        if not send_sms(phone, code):
            return Response({"detail": "SMS yuborishda xatolik."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"detail": "SMS kod yuborildi.", "phone": phone, "retry_after": _REG_RESEND_SECONDS})


def _check_code(phone, code, student):
    """(pending, error_response)"""
    key = _REG_KEY.format(phone)
    pending = cache.get(key)
    if not pending or pending.get("student_id") != student.id:
        return None, Response({"detail": "Kod muddati tugagan. Qaytadan kod oling."}, status=status.HTTP_400_BAD_REQUEST)
    if pending["code"] != str(code or "").strip():
        pending["tries"] += 1
        if pending["tries"] >= _REG_MAX_TRIES:
            cache.delete(key)
            return None, Response({"detail": "Urinishlar soni tugadi. Qaytadan kod oling."}, status=status.HTTP_400_BAD_REQUEST)
        cache.set(key, pending, _REG_TTL)
        return None, Response({"detail": "Kod noto'g'ri."}, status=status.HTTP_400_BAD_REQUEST)
    return pending, None


class ParentQrRegisterVerifyAPIView(APIView):
    """SMS kodni tekshiradi (keyingi qadam — parol qo'yish)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        student, phone, error = _resolve(request)
        if error:
            return error
        pending, error = _check_code(phone, request.data.get("code"), student)
        if error:
            return error
        pending["verified"] = True
        cache.set(_REG_KEY.format(phone), pending, _REG_TTL)
        return Response({"verified": True})


class ParentQrRegisterCompleteAPIView(APIView):
    """Parol qo'yiladi: ota-ona hisobi yaratiladi va farzand biriktiriladi. Keyin parent-qr/login/ bilan kiriladi."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        student, phone, error = _resolve(request)
        if error:
            return error
        password = str(request.data.get("password") or "")
        if len(password) < _MIN_PASSWORD:
            return Response(
                {"detail": f"Parol kamida {_MIN_PASSWORD} ta belgidan iborat bo'lsin."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pending, error = _check_code(phone, request.data.get("code"), student)
        if error:
            return error
        if not pending.get("verified"):
            return Response({"detail": "Avval SMS kodni tasdiqlang."}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(phone=phone).exists():
            cache.delete(_REG_KEY.format(phone))
            return Response({"detail": "Bu telefon raqam allaqachon ro'yxatdan o'tgan."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = User(phone=phone, role="parent", lang=pending.get("lang") or "uz")
            user.set_password(password)
            user.save()
            parent = Parent.objects.create(
                user=user, full_name=pending["full_name"], status=True, lang=pending.get("lang") or "uz",
            )
            _link(parent, student)
        cache.delete(_REG_KEY.format(phone))
        return Response({"created": True, "phone": phone}, status=status.HTTP_201_CREATED)
