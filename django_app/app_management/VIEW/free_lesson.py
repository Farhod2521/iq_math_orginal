"""
"Bepul darsga yoziling" arizalari.

POST  /api/v1/management/free-lesson/              — ochiq (bosh sahifa banneridagi forma)
GET   /api/v1/management/free-lesson/list/         — mentor / superadmin: ro'yxat, holatlar bo'yicha sonlar
PATCH /api/v1/management/free-lesson/list/<id>/    — mentor / superadmin: holat va izohni o'zgartirish

Yangi ariza haqida Telegram botga xabar telegram_bot/marketing.py orqali (har daqiqada) yuboriladi.
"""
import re
from datetime import timedelta

from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_management.models import FreeLessonRequest
from django_app.app_management.permissions import IsTeacherOrSuperAdmin

RATE_LIMIT = 5  # bir IP dan soatiga ko'pi bilan shuncha ariza
DUPLICATE_WINDOW = timedelta(minutes=10)


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    return (forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None


def _normalize_phone(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 9:
        digits = "998" + digits
    return digits if len(digits) == 12 and digits.startswith("998") else None


def serialize(item):
    return {
        "id": item.id,
        "parent_name": item.parent_name,
        "phone": item.phone,
        "class_num": item.class_num,
        "status": item.status,
        "status_display": item.get_status_display(),
        "note": item.note,
        "source": item.source,
        "handled_by": getattr(item.handled_by, "phone", None),
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


class FreeLessonCreateAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # forma tokensiz yuboriladi

    def post(self, request):
        name = str(request.data.get("parent_name") or "").strip()
        phone = _normalize_phone(request.data.get("phone"))
        class_num = request.data.get("class_num")

        errors = {}
        if len(name) < 2:
            errors["parent_name"] = "Ismingizni kiriting."
        if not phone:
            errors["phone"] = "Telefon raqamni to'g'ri kiriting (+998 XX XXX XX XX)."
        try:
            class_num = int(class_num) if class_num not in (None, "") else None
            if class_num is not None and not 1 <= class_num <= 11:
                raise ValueError
        except (TypeError, ValueError):
            errors["class_num"] = "Sinfni tanlang."
        if errors:
            return Response({"errors": errors, "detail": next(iter(errors.values()))}, status=status.HTTP_400_BAD_REQUEST)

        ip = _client_ip(request)
        key = f"free-lesson-rate:{ip}"
        if cache.get(key, 0) >= RATE_LIMIT:
            return Response(
                {"detail": "Juda ko'p ariza yuborildi. Birozdan keyin qayta urinib ko'ring."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        cache.set(key, cache.get(key, 0) + 1, 60 * 60)

        # Bir xil raqamdan qisqa vaqtda takror ariza — yangisi yaratilmaydi
        recent = FreeLessonRequest.objects.filter(phone=phone, created_at__gte=timezone.now() - DUPLICATE_WINDOW).first()
        if recent:
            return Response({"detail": "Arizangiz qabul qilindi.", "id": recent.id}, status=status.HTTP_200_OK)

        item = FreeLessonRequest.objects.create(
            parent_name=name[:150],
            phone=phone,
            class_num=class_num,
            source=str(request.data.get("source") or "home_banner")[:30],
            ip_address=ip,
        )
        return Response({"detail": "Arizangiz qabul qilindi.", "id": item.id}, status=status.HTTP_201_CREATED)


class FreeLessonListAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    def get(self, request):
        qs = FreeLessonRequest.objects.select_related("handled_by")
        status_filter = request.GET.get("status")
        if status_filter in dict(FreeLessonRequest.STATUS_CHOICES):
            qs = qs.filter(status=status_filter)
        search = (request.GET.get("search") or "").strip()
        if search:
            digits = re.sub(r"\D", "", search)
            query = Q(parent_name__icontains=search)
            if digits:
                query |= Q(phone__contains=digits)
            qs = qs.filter(query)

        try:
            page_size = min(max(int(request.GET.get("page_size", 20)), 1), 100)
            page_number = max(int(request.GET.get("page", 1)), 1)
        except ValueError:
            page_size, page_number = 20, 1
        page = Paginator(qs, page_size).get_page(page_number)

        now = timezone.now()
        counts = dict(FreeLessonRequest.objects.values_list("status").annotate(c=Count("id")))
        return Response({
            "count": page.paginator.count,
            "page": page.number,
            "pages": page.paginator.num_pages,
            "results": [serialize(item) for item in page.object_list],
            "counts": {key: counts.get(key, 0) for key, _ in FreeLessonRequest.STATUS_CHOICES},
            "total": sum(counts.values()),
            "last_7_days": FreeLessonRequest.objects.filter(created_at__gte=now - timedelta(days=7)).count(),
            "last_30_days": FreeLessonRequest.objects.filter(created_at__gte=now - timedelta(days=30)).count(),
        })

    def patch(self, request, pk):
        item = FreeLessonRequest.objects.filter(pk=pk).first()
        if item is None:
            return Response({"detail": "Ariza topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        new_status = request.data.get("status")
        if new_status is not None:
            if new_status not in dict(FreeLessonRequest.STATUS_CHOICES):
                return Response({"detail": "Holat noto'g'ri."}, status=status.HTTP_400_BAD_REQUEST)
            item.status = new_status
        if "note" in request.data:
            item.note = str(request.data.get("note") or "")[:2000]
        item.handled_by = request.user
        item.save()
        return Response(serialize(item))
