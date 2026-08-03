import hashlib
import logging
import uuid
from datetime import timedelta

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import Category, Tag, Book, BookPurchase, OfflineBookOrder, BookPayment
from .serializers import CategorySerializer, TagSerializer, BookReadSerializer, BookWriteSerializer
from django_app.app_management.models import ConversionRate
from django_app.app_student.models import StudentScore
from django_app.app_payments.utils import (
    get_multicard_token,
    get_payment_pending_timeout_minutes,
    MULTICARD_BASE_URL,
    MULTICARD_STORE_ID,
    SECRET_KEY as MULTICARD_SECRET_KEY,
)

logger = logging.getLogger(__name__)

# Kitob to'lovi uchun OFD (soliq) ma'lumotlari.
# TODO: kitob uchun haqiqiy MXIK va package_code ni soliq organidan olib, settings orqali almashtiring.
BOOK_OFD_PACKAGE_CODE = getattr(settings, "BOOK_OFD_PACKAGE_CODE", "1165336")
BOOK_OFD_MXIK = getattr(settings, "BOOK_OFD_MXIK", "10899001001000000")

# Multicard to'lovdan keyin foydalanuvchini qaytaradigan / callback yuboradigan manzillar.
BOOK_PAYMENT_RETURN_URL = getattr(settings, "BOOK_PAYMENT_RETURN_URL", "https://iqmath.uz/dashboard/library")
BOOK_PAYMENT_CALLBACK_URL = getattr(
    settings, "BOOK_PAYMENT_CALLBACK_URL", "https://api.iqmath.uz/api/v1/book/payment-callback/"
)


def calc_book_prices(book, rate):
    """
    Kitob narxini uchala valyutada qaytaradi: (so'm, tanga, ball).
    `rate` — ConversionRate obyekti.
    """
    price_som = float(book.price)
    coin_to_money = float(rate.coin_to_money)
    coin_to_score = int(rate.coin_to_score)

    price_coin = round(price_som / coin_to_money, 2) if coin_to_money else 0
    price_score = round(price_coin * coin_to_score, 2)
    return price_som, price_coin, price_score


def expire_pending_book_payments(user=None):
    """Muddati o'tgan pending kitob to'lovlarini failed holatiga o'tkazadi."""
    now = timezone.now()
    cutoff = now - timedelta(minutes=get_payment_pending_timeout_minutes())
    qs = BookPayment.objects.filter(status='pending', created_at__lt=cutoff)
    if user is not None:
        qs = qs.filter(user=user)
    return qs.update(status='failed', updated_at=now)


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'role', None) == 'superadmin'
        )


# ─────────────────────────────────────────────
#  CATEGORY CRUD
# ─────────────────────────────────────────────
class CategoryCRUDAPIView(APIView):
    """
    GET    /book/categories/        → list
    POST   /book/categories/        → create  (superadmin)
    GET    /book/categories/<pk>/   → detail
    PUT    /book/categories/<pk>/   → update  (superadmin)
    DELETE /book/categories/<pk>/   → delete  (superadmin)
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsSuperAdmin()]

    def get(self, request, pk=None):
        if pk:
            try:
                obj = Category.objects.get(pk=pk)
            except Category.DoesNotExist:
                return Response({"detail": "Kategoriya topilmadi."}, status=404)
            return Response(CategorySerializer(obj).data)

        qs = Category.objects.all()
        if request.GET.get('active'):
            qs = qs.filter(is_active=True)
        return Response(CategorySerializer(qs, many=True).data)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            obj = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({"detail": "Kategoriya topilmadi."}, status=404)
        serializer = CategorySerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            obj = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return Response({"detail": "Kategoriya topilmadi."}, status=404)
        obj.delete()
        return Response({"detail": "Kategoriya o'chirildi."}, status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
#  TAG CRUD
# ─────────────────────────────────────────────
class TagCRUDAPIView(APIView):
    """
    GET    /book/tags/        → list
    POST   /book/tags/        → create  (superadmin)
    GET    /book/tags/<pk>/   → detail
    PUT    /book/tags/<pk>/   → update  (superadmin)
    DELETE /book/tags/<pk>/   → delete  (superadmin)
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsSuperAdmin()]

    def get(self, request, pk=None):
        if pk:
            try:
                obj = Tag.objects.get(pk=pk)
            except Tag.DoesNotExist:
                return Response({"detail": "Teg topilmadi."}, status=404)
            return Response(TagSerializer(obj).data)

        qs = Tag.objects.all()
        if request.GET.get('active'):
            qs = qs.filter(is_active=True)
        return Response(TagSerializer(qs, many=True).data)

    def post(self, request):
        serializer = TagSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            obj = Tag.objects.get(pk=pk)
        except Tag.DoesNotExist:
            return Response({"detail": "Teg topilmadi."}, status=404)
        serializer = TagSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            obj = Tag.objects.get(pk=pk)
        except Tag.DoesNotExist:
            return Response({"detail": "Teg topilmadi."}, status=404)
        obj.delete()
        return Response({"detail": "Teg o'chirildi."}, status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
#  BOOK CRUD
# ─────────────────────────────────────────────
class BookCRUDAPIView(APIView):
    """
    GET    /book/books/        → list   (filter: ?category=<id>, ?status=active, ?tag=<id>)
    POST   /book/books/        → create (superadmin)
    GET    /book/books/<pk>/   → detail
    PUT    /book/books/<pk>/   → update (superadmin)
    DELETE /book/books/<pk>/   → delete (superadmin)
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsSuperAdmin()]

    def get(self, request, pk=None):
        if pk:
            try:
                obj = Book.objects.select_related('category').prefetch_related('tags').get(pk=pk)
            except Book.DoesNotExist:
                return Response({"detail": "Kitob topilmadi."}, status=404)
            return Response(BookReadSerializer(obj).data)

        qs = Book.objects.select_related('category').prefetch_related('tags')

        category_id = request.GET.get('category')
        status_filter = request.GET.get('status')
        tag_id = request.GET.get('tag')
        for_student = request.GET.get('for_student')
        for_teacher = request.GET.get('for_teacher')

        if category_id:
            qs = qs.filter(category__id=category_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if tag_id:
            qs = qs.filter(tags__id=tag_id)
        if for_student is not None:
            qs = qs.filter(for_student=for_student.lower() == 'true')
        if for_teacher is not None:
            qs = qs.filter(for_teacher=for_teacher.lower() == 'true')

        return Response(BookReadSerializer(qs, many=True).data)

    def post(self, request):
        serializer = BookWriteSerializer(data=request.data)
        if serializer.is_valid():
            book = serializer.save()
            return Response(BookReadSerializer(book).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            obj = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response({"detail": "Kitob topilmadi."}, status=404)
        serializer = BookWriteSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            book = serializer.save()
            return Response(BookReadSerializer(book).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            obj = Book.objects.get(pk=pk)
        except Book.DoesNotExist:
            return Response({"detail": "Kitob topilmadi."}, status=404)
        obj.delete()
        return Response({"detail": "Kitob o'chirildi."}, status=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────
#  FOYDALANUVCHI UCHUN KITOBLAR (role asosida)
# ─────────────────────────────────────────────
class BookListForUserAPIView(APIView):
    """
    GET /book/my-books/
    GET /book/my-books/<pk>/

    Role asosida filtrlaydi:
      - student → for_student=True kitoblar
      - tutor   → for_teacher=True kitoblar
      - superadmin/admin → barcha active kitoblar

    Narx ham so'm, ham coin da qaytadi (ConversionRate dan hisoblanadi).
    """
    permission_classes = [IsAuthenticated]

    def _get_coin_rate(self):
        rate = ConversionRate.objects.first()
        if not rate:
            return None, None
        return rate.coin_to_money, rate.coin_to_score

    def _serialize(self, book, coin_to_money, coin_to_score):
        price_som  = float(book.price)
        price_coin  = round(price_som / float(coin_to_money), 2) if coin_to_money else None
        price_score = round(price_coin * coin_to_score, 2) if (price_coin and coin_to_score) else None

        category = book.category
        tags = book.tags.all()

        return {
            "id":   book.id,
            "name_uz": book.name_uz,
            "name_ru": book.name_ru,
            "description_uz": book.description_uz,
            "description_ru": book.description_ru,

            "category": {
                "id":      category.id      if category else None,
                "name_uz": category.name_uz if category else None,
                "name_ru": category.name_ru if category else None,
            } if category else None,

            "tags": [
                {"id": t.id, "name_uz": t.name_uz, "name_ru": t.name_ru}
                for t in tags
            ],

            "cover_image": book.cover_image.url if book.cover_image else None,
            "file":        book.file.url        if book.file        else None,

            "price_som":   price_som,
            "price_coin":  price_coin,
            "price_score": price_score,

            "status":      book.status,
            "is_offline":  book.is_offline,
            "quantity":    book.quantity,
            "for_student": book.for_student,
            "for_teacher": book.for_teacher,
            "date":        str(book.date),
        }

    def _base_qs(self, request):
        role = getattr(request.user, 'role', None)
        qs = Book.objects.select_related('category').prefetch_related('tags').filter(status='active')

        if role == 'student':
            qs = qs.filter(for_student=True)
        elif role == 'tutor':
            qs = qs.filter(for_teacher=True)
        # superadmin/admin — barcha active kitoblar

        return qs

    def get(self, request, pk=None):
        coin_to_money, coin_to_score = self._get_coin_rate()

        if pk:
            qs = self._base_qs(request)
            try:
                book = qs.get(pk=pk)
            except Book.DoesNotExist:
                return Response({"detail": "Kitob topilmadi."}, status=404)
            return Response(self._serialize(book, coin_to_money, coin_to_score))

        qs = self._base_qs(request)

        # Qo'shimcha filterlar
        category_id = request.GET.get('category')
        tag_id      = request.GET.get('tag')
        is_offline  = request.GET.get('is_offline')

        if category_id:
            qs = qs.filter(category__id=category_id)
        if tag_id:
            qs = qs.filter(tags__id=tag_id)
        if is_offline is not None:
            qs = qs.filter(is_offline=is_offline.lower() == 'true')

        data = [self._serialize(b, coin_to_money, coin_to_score) for b in qs]
        return Response({"count": len(data), "results": data})


# ─────────────────────────────────────────────
#  KITOB SOTIB OLISH
# ─────────────────────────────────────────────
class BookPurchaseAPIView(APIView):
    """
    POST /book/purchase/
    Body: { "book_id": 1, "payment_method": "coin" }
         payment_method: "som" | "coin" | "score"

    GET  /book/purchase/   → o"zi sotib olgan kitoblar ro'yxati"
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = getattr(request.user, 'role', None)

        base_qs = BookPurchase.objects.select_related(
            'book__category', 'user',
        ).prefetch_related('book__tags').order_by('-purchased_at')

        if role in ('superadmin', 'admin'):
            qs = base_qs

            role_filter = request.GET.get('role')
            if role_filter:
                qs = qs.filter(user__role=role_filter)

            book_id = request.GET.get('book_id')
            if book_id:
                qs = qs.filter(book__id=book_id)

            payment_method = request.GET.get('payment_method')
            if payment_method:
                qs = qs.filter(payment_method=payment_method)

        elif role in ('student', 'tutor'):
            qs = base_qs.filter(user=request.user)
        else:
            return Response({"detail": "Ruxsat yo'q."}, status=403)

        for_user = role in ('student', 'tutor')
        data = [self._serialize_purchase(p, for_user=for_user) for p in qs]
        return Response({"count": len(data), "results": data})

    def post(self, request):
        role = getattr(request.user, 'role', None)
        if role not in ('student', 'tutor'):
            return Response({"detail": "Faqat student yoki tutor uchun."}, status=403)

        book_id          = request.data.get('book_id')
        payment_method   = request.data.get('payment_method')
        quantity         = int(request.data.get('quantity', 1))
        delivery_address = request.data.get('delivery_address', '').strip()
        delivery_phone   = request.data.get('delivery_phone', '').strip()

        if not book_id:
            return Response({"detail": "book_id talab qilinadi."}, status=400)
        if quantity < 1:
            return Response({"detail": "quantity kamida 1 bo'lishi kerak."}, status=400)
        if role == 'tutor' and payment_method != 'som':
            return Response({"detail": "Tutor faqat so'm bilan to'lay oladi."}, status=400)
        if payment_method not in ('som', 'coin', 'score'):
            return Response({"detail": "payment_method: 'som', 'coin' yoki 'score' bo'lishi kerak."}, status=400)

        try:
            book = Book.objects.get(pk=book_id, status='active')
        except Book.DoesNotExist:
            return Response({"detail": "Kitob topilmadi."}, status=404)

        # Oflayn kitob uchun manzil va telefon majburiy
        if book.is_offline:
            if not delivery_address:
                return Response({"detail": "Oflayn kitob uchun delivery_address talab qilinadi."}, status=400)
            if not delivery_phone:
                return Response({"detail": "Oflayn kitob uchun delivery_phone talab qilinadi."}, status=400)

        if BookPurchase.objects.filter(user=request.user, book=book).exists():
            return Response({"detail": "Siz bu kitobni allaqachon sotib olgansiz."}, status=400)

        rate = ConversionRate.objects.first()
        if not rate:
            return Response({"detail": "Konversiya kursi topilmadi."}, status=500)

        price_som     = float(book.price)
        coin_to_money = float(rate.coin_to_money)
        coin_to_score = int(rate.coin_to_score)

        if payment_method == 'som':
            unit_price = price_som
        elif payment_method == 'coin':
            unit_price = round(price_som / coin_to_money, 2)
        else:
            unit_price = round((price_som / coin_to_money) * coin_to_score, 2)

        paid_amount = round(unit_price * quantity, 2)
        remaining = {}

        with transaction.atomic():
            if role == 'student':
                student = getattr(request.user, 'student_profile', None)
                try:
                    student_score = StudentScore.objects.get(student=student)
                except StudentScore.DoesNotExist:
                    return Response({"detail": "Student balansi topilmadi."}, status=400)

                # Balans yetarli emasmi? Unda karta orqali to'lash imkoniyatini qaytaramiz.
                balance_map = {
                    'som':   (student_score.som,   "So'm"),
                    'coin':  (student_score.coin,  "Tanga"),
                    'score': (student_score.score, "Ball"),
                }
                balance, label = balance_map[payment_method]

                if balance < paid_amount:
                    payable_som = round(price_som * quantity, 2)
                    return Response({
                        "detail": (
                            f"{label} yetarli emas. Balans: {balance}, kerak: {paid_amount}. "
                            f"Kitobni {payable_som:,.0f} so'mga karta orqali sotib olishingiz mumkin."
                        ),
                        "code":            "insufficient_balance",
                        "payment_method":  payment_method,
                        "required":        paid_amount,
                        "balance":         balance,
                        "shortage":        round(paid_amount - balance, 2),
                        # Karta orqali to'lash uchun /book/initiate-payment/ ga murojaat qilinadi
                        "payment_required": True,
                        "payable_som":     payable_som,
                        "book_id":         book.id,
                        "quantity":        quantity,
                    }, status=400)

                if payment_method == 'som':
                    student_score.som -= int(paid_amount)
                elif payment_method == 'coin':
                    student_score.coin -= int(paid_amount)
                else:
                    student_score.score -= int(paid_amount)
                student_score.save()
                remaining = {"som": student_score.som, "coin": student_score.coin, "score": student_score.score}

            purchase = BookPurchase.objects.create(
                user=request.user,
                book=book,
                quantity=quantity,
                payment_method=payment_method,
                paid_amount=paid_amount,
            )

            # Oflayn kitob uchun buyurtma yozivi
            if book.is_offline:
                OfflineBookOrder.objects.create(
                    purchase=purchase,
                    delivery_address=delivery_address,
                    phone=delivery_phone,
                )

        response_data = {
            "detail":            "Kitob muvaffaqiyatli sotib olindi.",
            "purchase_id":       purchase.id,
            "book_name_uz":      book.name_uz,
            "book_name_ru":      book.name_ru,
            "is_offline":        book.is_offline,
            "quantity":          quantity,
            "unit_price":        unit_price,
            "paid_amount":       paid_amount,
            "payment_method":    payment_method,
            "purchased_at":      purchase.purchased_at.strftime("%d/%m/%Y %H:%M"),
            "remaining_balance": remaining,
        }

        if book.is_offline:
            response_data["delivery_status"] = "new"
            response_data["delivery_address"] = delivery_address
            response_data["delivery_phone"]   = delivery_phone
        else:
            # Online kitob — faylni yuklab olish havolasi
            response_data["file"] = book.file.url if book.file else None

        return Response(response_data, status=201)

    def _serialize_purchase(self, p, for_user=False):
        book = p.book
        user = p.user
        user_role = getattr(user, 'role', None)

        full_name = None
        if user_role == 'student':
            profile = getattr(user, 'student_profile', None)
            full_name = getattr(profile, 'full_name', None)
        elif user_role in ('tutor', 'teacher'):
            profile = getattr(user, 'tutor_profile', None)
            full_name = getattr(profile, 'full_name', None)

        result = {
            "purchase_id":    p.id,
            "purchased_at":   p.purchased_at.strftime("%d/%m/%Y %H:%M"),
            "payment_method": p.payment_method,
            "quantity":       p.quantity,
            "paid_amount":    float(p.paid_amount),
            "book": {
                "id":          book.id,
                "name_uz":     book.name_uz,
                "name_ru":     book.name_ru,
                "cover_image": book.cover_image.url if book.cover_image else None,
                "is_offline":  book.is_offline,
            },
        }

        if not for_user:
            result["user"] = {
                "id":        user.id,
                "phone":     getattr(user, 'phone', None),
                "role":      user_role,
                "full_name": full_name,
            }

        if book.is_offline:
            try:
                order = p.offline_order
                result["offline_order"] = {
                    "order_id":        order.id,
                    "delivery_status": order.delivery_status,
                    "delivery_status_display": order.get_delivery_status_display(),
                    "delivery_address": order.delivery_address,
                    "phone":           order.phone,
                    "admin_note":      order.admin_note,
                    "updated_at":      order.updated_at.strftime("%d/%m/%Y %H:%M"),
                }
            except OfflineBookOrder.DoesNotExist:
                result["offline_order"] = None
        else:
            # Online kitob — yuklab olish havolasi
            result["book"]["file"] = book.file.url if book.file else None

        return result


# ─────────────────────────────────────────────
#  FOYDALANUVCHI SOTIB OLGAN KITOBLARI
# ─────────────────────────────────────────────
class MyPurchasedBooksAPIView(APIView):
    """
    GET /book/my-purchases/              → barcha sotib olingan kitoblar
    GET /book/my-purchases/?type=online  → faqat online kitoblar (fayl bilan)
    GET /book/my-purchases/?type=offline → faqat offline kitoblar (status bilan)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = getattr(request.user, 'role', None)
        if role not in ('student', 'tutor'):
            return Response({"detail": "Ruxsat yo'q."}, status=403)

        qs = BookPurchase.objects.select_related(
            'book__category', 'user'
        ).prefetch_related('book__tags').filter(
            user=request.user
        ).order_by('-purchased_at')

        type_filter = request.GET.get('type', '').strip().lower()
        if type_filter == 'online':
            qs = qs.filter(book__is_offline=False)
        elif type_filter == 'offline':
            qs = qs.filter(book__is_offline=True)

        online_list  = []
        offline_list = []

        for p in qs:
            data = self._serialize(p)
            if p.book.is_offline:
                offline_list.append(data)
            else:
                online_list.append(data)

        if type_filter == 'online':
            return Response({"count": len(online_list), "results": online_list})
        elif type_filter == 'offline':
            return Response({"count": len(offline_list), "results": offline_list})

        return Response({
            "online_count":  len(online_list),
            "offline_count": len(offline_list),
            "online_books":  online_list,
            "offline_books": offline_list,
        })

    def _serialize(self, p):
        book = p.book
        result = {
            "purchase_id":    p.id,
            "purchased_at":   p.purchased_at.strftime("%d/%m/%Y %H:%M"),
            "payment_method": p.payment_method,
            "quantity":       p.quantity,
            "paid_amount":    float(p.paid_amount),
            "book": {
                "id":          book.id,
                "name_uz":     book.name_uz,
                "name_ru":     book.name_ru,
                "cover_image": book.cover_image.url if book.cover_image else None,
                "is_offline":  book.is_offline,
            },
        }
        if book.is_offline:
            try:
                order = p.offline_order
                result["delivery_status"]         = order.delivery_status
                result["delivery_status_display"] = order.get_delivery_status_display()
                result["delivery_address"]         = order.delivery_address
                result["phone"]                    = order.phone
                result["admin_note"]               = order.admin_note
                result["updated_at"]               = order.updated_at.strftime("%d/%m/%Y %H:%M")
            except OfflineBookOrder.DoesNotExist:
                result["delivery_status"] = None
        else:
            result["book"]["file"] = book.file.url if book.file else None

        return result


# ─────────────────────────────────────────────
#  ADMIN: OFFLINE BUYURTMALAR
# ─────────────────────────────────────────────
class AdminOfflineOrderAPIView(APIView):
    """
    GET /book/offline-orders/          → barcha offline buyurtmalar (admin/superadmin)
    GET /book/offline-orders/<pk>/     → bitta buyurtma
    PUT /book/offline-orders/<pk>/     → statusni yangilash
        Body: { "delivery_status": "seen"|"preparing"|"delivering"|"delivered", "admin_note": "..." }
    """
    permission_classes = [IsAuthenticated]

    def _check_admin(self, user):
        return getattr(user, 'role', None) in ('admin', 'superadmin', 'teacher')

    def get(self, request, pk=None):
        if not self._check_admin(request.user):
            return Response({"detail": "Faqat admin uchun."}, status=403)

        if pk:
            try:
                order = OfflineBookOrder.objects.select_related(
                    'purchase__book', 'purchase__user'
                ).get(pk=pk)
            except OfflineBookOrder.DoesNotExist:
                return Response({"detail": "Buyurtma topilmadi."}, status=404)
            return Response(self._serialize(order))

        qs = OfflineBookOrder.objects.select_related(
            'purchase__book', 'purchase__user'
        ).order_by('-created_at')

        status_filter = request.GET.get('status')
        if status_filter:
            qs = qs.filter(delivery_status=status_filter)

        return Response({"count": qs.count(), "results": [self._serialize(o) for o in qs]})

    def put(self, request, pk):
        if not self._check_admin(request.user):
            return Response({"detail": "Faqat admin uchun."}, status=403)

        try:
            order = OfflineBookOrder.objects.select_related(
                'purchase__book', 'purchase__user'
            ).get(pk=pk)
        except OfflineBookOrder.DoesNotExist:
            return Response({"detail": "Buyurtma topilmadi."}, status=404)

        new_status = request.data.get('delivery_status')
        admin_note = request.data.get('admin_note')

        valid_statuses = [s[0] for s in OfflineBookOrder.STATUS_CHOICES]
        if new_status and new_status not in valid_statuses:
            return Response({
                "detail": f"Noto'g'ri status. Mumkin bo'lganlar: {valid_statuses}"
            }, status=400)

        if new_status:
            order.delivery_status = new_status
        if admin_note is not None:
            order.admin_note = admin_note
        order.save()

        return Response({
            "detail":                  "Buyurtma holati yangilandi.",
            "order_id":                order.id,
            "delivery_status":         order.delivery_status,
            "delivery_status_display": order.get_delivery_status_display(),
            "admin_note":              order.admin_note,
            "updated_at":              order.updated_at.strftime("%d/%m/%Y %H:%M"),
        })

    def _serialize(self, order):
        p    = order.purchase
        book = p.book
        user = p.user

        full_name = None
        if user.role == 'student':
            profile = getattr(user, 'student_profile', None)
            full_name = getattr(profile, 'full_name', None)
        elif user.role == 'tutor':
            profile = getattr(user, 'tutor_profile', None)
            full_name = getattr(profile, 'full_name', None)

        return {
            "order_id":                order.id,
            "delivery_status":         order.delivery_status,
            "delivery_status_display": order.get_delivery_status_display(),
            "delivery_address":        order.delivery_address,
            "phone":                   order.phone,
            "admin_note":              order.admin_note,
            "created_at":              order.created_at.strftime("%d/%m/%Y %H:%M"),
            "updated_at":              order.updated_at.strftime("%d/%m/%Y %H:%M"),
            "purchase": {
                "purchase_id":    p.id,
                "purchased_at":   p.purchased_at.strftime("%d/%m/%Y %H:%M"),
                "payment_method": p.payment_method,
                "quantity":       p.quantity,
                "paid_amount":    float(p.paid_amount),
            },
            "user": {
                "id":        user.id,
                "phone":     user.phone,
                "role":      user.role,
                "full_name": full_name,
            },
            "book": {
                "id":          book.id,
                "name_uz":     book.name_uz,
                "name_ru":     book.name_ru,
                "cover_image": book.cover_image.url if book.cover_image else None,
            },
        }


# ─────────────────────────────────────────────
#  KITOBNI KARTA ORQALI SOTIB OLISH (MULTICARD)
# ─────────────────────────────────────────────
class BookInitiatePaymentAPIView(APIView):
    """
    POST /book/initiate-payment/
    Body: {
        "book_id": 1,
        "quantity": 1,
        "delivery_address": "...",   # faqat oflayn kitob uchun
        "delivery_phone":   "+998901234567"
    }

    Tanga / ball / so'm balansi yetmaganda foydalanuvchi kitobni to'liq so'm
    summasi bilan karta orqali sotib oladi. Javobdagi `checkout_url` ga
    yo'naltiriladi, to'lov tasdiqlangach `BookPurchase` avtomatik yaratiladi.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        role = getattr(request.user, 'role', None)
        if role not in ('student', 'tutor'):
            return Response({"detail": "Faqat student yoki tutor uchun."}, status=403)

        book_id          = request.data.get('book_id')
        delivery_address = (request.data.get('delivery_address') or '').strip()
        delivery_phone   = (request.data.get('delivery_phone') or '').strip()

        if not book_id:
            return Response({"detail": "book_id talab qilinadi."}, status=400)

        try:
            quantity = int(request.data.get('quantity', 1))
        except (TypeError, ValueError):
            return Response({"detail": "quantity butun son bo'lishi kerak."}, status=400)
        if quantity < 1:
            return Response({"detail": "quantity kamida 1 bo'lishi kerak."}, status=400)

        try:
            book = Book.objects.get(pk=book_id, status='active')
        except Book.DoesNotExist:
            return Response({"detail": "Kitob topilmadi."}, status=404)

        if book.quantity is not None and quantity > book.quantity:
            return Response({"detail": f"Omborda faqat {book.quantity} dona mavjud."}, status=400)

        # Oflayn kitob uchun manzil va telefon majburiy
        if book.is_offline:
            if not delivery_address:
                return Response({"detail": "Oflayn kitob uchun delivery_address talab qilinadi."}, status=400)
            if not delivery_phone:
                return Response({"detail": "Oflayn kitob uchun delivery_phone talab qilinadi."}, status=400)

        if BookPurchase.objects.filter(user=request.user, book=book).exists():
            return Response({"detail": "Siz bu kitobni allaqachon sotib olgansiz."}, status=400)

        unit_price = float(book.price)
        if unit_price <= 0:
            return Response({"detail": "Bu kitob bepul, onlayn to'lov talab qilinmaydi."}, status=400)

        amount = round(unit_price * quantity, 2)

        # Muddati o'tgan pending to'lovlarni yopamiz
        expire_pending_book_payments(user=request.user)

        try:
            token = get_multicard_token()
        except Exception as e:
            logger.error(f"Multicard token error (book): {e}")
            return Response({"error": "Token olishda xatolik", "details": str(e)}, status=500)

        transaction_id     = str(uuid.uuid4())
        amount_in_tiyin    = int(round(amount * 100))
        unit_price_in_tiyin = int(round(unit_price * 100))

        book_title = (book.name_uz or book.name_ru or book.name or '').strip()
        ofd_name   = f"IQMATH.UZ — {book_title} (kitob)"[:250]

        payload = {
            "store_id":     MULTICARD_STORE_ID,
            "amount":       amount_in_tiyin,
            "invoice_id":   transaction_id,
            "return_url":   BOOK_PAYMENT_RETURN_URL,
            "callback_url": BOOK_PAYMENT_CALLBACK_URL,
            "ofd": [
                {
                    "vat":          0,
                    "price":        unit_price_in_tiyin,
                    "qty":          quantity,
                    "name":         ofd_name,
                    "package_code": BOOK_OFD_PACKAGE_CODE,
                    "mxik":         BOOK_OFD_MXIK,
                    "total":        amount_in_tiyin,
                }
            ],
        }

        try:
            response = requests.post(
                f"{MULTICARD_BASE_URL}/payment/invoice",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Multicard connection error (book): {e}")
            return Response({"error": "Multicard bilan bog'lanishda xatolik", "details": str(e)}, status=500)

        if response.status_code != 200:
            logger.error(f"Multicard invoice error (book): {response.text}")
            return Response({"error": "To'lov yaratilishda xatolik", "details": response.text}, status=500)

        payment_data = response.json()
        checkout_url = (payment_data.get('data') or {}).get('checkout_url')

        book_payment = BookPayment.objects.create(
            user=request.user,
            book=book,
            quantity=quantity,
            unit_price=unit_price,
            amount=amount,
            transaction_id=transaction_id,
            status='pending',
            payment_gateway='multicard',
            checkout_url=checkout_url,
            delivery_address=delivery_address or None,
            delivery_phone=delivery_phone or None,
        )

        return Response({
            "payment_data":    payment_data,
            "checkout_url":    checkout_url,
            "transaction_id":  transaction_id,
            "book_payment_id": book_payment.id,
            "book": {
                "id":          book.id,
                "name_uz":     book.name_uz,
                "name_ru":     book.name_ru,
                "cover_image": book.cover_image.url if book.cover_image else None,
                "is_offline":  book.is_offline,
            },
            "quantity":   quantity,
            "unit_price": unit_price,
            "amount":     amount,
            "status":     book_payment.status,
        }, status=200)


class BookPaymentCallbackAPIView(APIView):
    """
    POST /book/payment-callback/  — Multicard callback.

    Imzo to'g'ri bo'lsa: BookPayment "success" ga o'tadi va BookPurchase
    (oflayn kitob bo'lsa OfflineBookOrder bilan birga) yaratiladi.
    """
    authentication_classes = []
    permission_classes = []

    def generate_sign(self, store_id, invoice_id, amount, secret):
        raw = f"{store_id}{invoice_id}{amount}{secret}"
        return hashlib.md5(raw.encode()).hexdigest()

    def post(self, request):
        try:
            expire_pending_book_payments()
            data = request.data
            logger.info(f"🔔 Book payment callback received: {data}")

            store_id      = str(data.get("store_id", ""))
            invoice_id    = str(data.get("invoice_id", ""))
            amount        = str(data.get("amount", ""))
            received_sign = data.get("sign", "")
            uuid_val      = data.get("uuid")
            invoice_uuid  = data.get("invoice_uuid")
            billing_id    = data.get("billing_id")

            expected_sign = self.generate_sign(store_id, invoice_id, amount, MULTICARD_SECRET_KEY)
            if received_sign != expected_sign:
                logger.error(f"❌ Book callback invalid signature. Expected: {expected_sign}, got: {received_sign}")
                return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                payment = BookPayment.objects.select_related('book', 'user').get(transaction_id=invoice_id)
            except BookPayment.DoesNotExist:
                logger.error(f"❌ BookPayment not found: {invoice_id}")
                return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

            # Idempotentlik — Multicard callbackni bir necha marta yuborishi mumkin
            if payment.status == 'success':
                logger.info(f"ℹ️ Book payment already processed: {payment.id}")
                return Response({"status": "ok", "message": "Already processed"}, status=status.HTTP_200_OK)

            with transaction.atomic():
                payment.store_id     = store_id
                payment.invoice_uuid = invoice_uuid
                payment.uuid         = uuid_val
                payment.billing_id   = billing_id
                payment.sign         = received_sign
                payment.status       = 'success'
                payment.payment_date = timezone.now()
                payment.receipt_url  = f"{MULTICARD_BASE_URL}/invoice/{uuid_val}"

                purchase, created = BookPurchase.objects.get_or_create(
                    user=payment.user,
                    book=payment.book,
                    defaults={
                        "quantity":       payment.quantity,
                        "payment_method": 'card',
                        "paid_amount":    payment.amount,
                    },
                )
                payment.purchase = purchase
                payment.save()

                if payment.book.is_offline and created:
                    OfflineBookOrder.objects.create(
                        purchase=purchase,
                        delivery_address=payment.delivery_address or '',
                        phone=payment.delivery_phone or '',
                    )

            logger.info(f"🎉 Book payment processed: payment={payment.id}, purchase={purchase.id}")
            return Response({"status": "ok", "message": "Payment processed successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"💥 Book payment callback error: {e}", exc_info=True)
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MyBookPaymentsAPIView(APIView):
    """
    GET /book/my-payments/                       → o'z kitob to'lovlari ro'yxati
    GET /book/my-payments/?transaction_id=<uuid> → bitta to'lov holati

    Foydalanuvchi to'lov sahifasidan qaytgach, frontend shu endpoint orqali
    to'lov tasdiqlanganini tekshiradi.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        expire_pending_book_payments(user=request.user)

        qs = BookPayment.objects.select_related('book', 'purchase').filter(user=request.user)

        transaction_id = request.GET.get('transaction_id')
        if transaction_id:
            payment = qs.filter(transaction_id=transaction_id).first()
            if not payment:
                return Response({"detail": "To'lov topilmadi."}, status=404)
            return Response(self._serialize(payment))

        status_filter = request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        data = [self._serialize(p) for p in qs]
        return Response({"count": len(data), "results": data})

    def _serialize(self, p):
        book = p.book
        return {
            "id":             p.id,
            "transaction_id": p.transaction_id,
            "status":         p.status,
            "status_display": p.get_status_display(),
            "quantity":       p.quantity,
            "unit_price":     float(p.unit_price),
            "amount":         float(p.amount),
            "checkout_url":   p.checkout_url,
            "receipt_url":    p.receipt_url,
            "purchase_id":    p.purchase_id,
            "created_at":     p.created_at.strftime("%d/%m/%Y %H:%M"),
            "payment_date":   p.payment_date.strftime("%d/%m/%Y %H:%M") if p.payment_date else None,
            "book": {
                "id":          book.id,
                "name_uz":     book.name_uz,
                "name_ru":     book.name_ru,
                "cover_image": book.cover_image.url if book.cover_image else None,
                "is_offline":  book.is_offline,
                "file":        book.file.url if (book.file and p.status == 'success' and not book.is_offline) else None,
            },
        }
