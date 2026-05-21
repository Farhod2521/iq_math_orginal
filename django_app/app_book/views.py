from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.db import transaction

from .models import Category, Tag, Book, BookPurchase
from .serializers import CategorySerializer, TagSerializer, BookReadSerializer, BookWriteSerializer
from django_app.app_management.models import ConversionRate
from django_app.app_student.models import StudentScore


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

    GET  /book/purchase/   → o'zi sotib olgan kitoblar ro'yxati
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

        data = [self._serialize_purchase(p) for p in qs]
        return Response({"count": len(data), "results": data})

    def post(self, request):
        role = getattr(request.user, 'role', None)
        if role not in ('student', 'tutor'):
            return Response({"detail": "Faqat student yoki tutor uchun."}, status=403)

        book_id        = request.data.get('book_id')
        payment_method = request.data.get('payment_method')
        quantity       = int(request.data.get('quantity', 1))

        if not book_id:
            return Response({"detail": "book_id talab qilinadi."}, status=400)
        if quantity < 1:
            return Response({"detail": "quantity kamida 1 bo'lishi kerak."}, status=400)

        # Tutor faqat som bilan to'lay oladi (balans tizimi yo'q)
        if role == 'tutor' and payment_method != 'som':
            return Response({"detail": "Tutor faqat so'm bilan to'lay oladi."}, status=400)
        if payment_method not in ('som', 'coin', 'score'):
            return Response({"detail": "payment_method: 'som', 'coin' yoki 'score' bo'lishi kerak."}, status=400)

        try:
            book = Book.objects.get(pk=book_id, status='active')
        except Book.DoesNotExist:
            return Response({"detail": "Kitob topilmadi."}, status=404)

        if BookPurchase.objects.filter(user=request.user, book=book).exists():
            return Response({"detail": "Siz bu kitobni allaqachon sotib olgansiz."}, status=400)

        rate = ConversionRate.objects.first()
        if not rate:
            return Response({"detail": "Konversiya kursi topilmadi."}, status=500)

        price_som     = float(book.price)
        coin_to_money = float(rate.coin_to_money)
        coin_to_score = int(rate.coin_to_score)

        # Bitta dona narxi
        if payment_method == 'som':
            unit_price = price_som
        elif payment_method == 'coin':
            unit_price = round(price_som / coin_to_money, 2)
        else:
            unit_price = round((price_som / coin_to_money) * coin_to_score, 2)

        # Jami summa = bitta narx × miqdor
        paid_amount = round(unit_price * quantity, 2)

        remaining = {}

        with transaction.atomic():
            if role == 'student':
                student = getattr(request.user, 'student_profile', None)
                try:
                    student_score = StudentScore.objects.get(student=student)
                except StudentScore.DoesNotExist:
                    return Response({"detail": "Student balansi topilmadi."}, status=400)

                if payment_method == 'som' and student_score.som < paid_amount:
                    return Response({"detail": f"So'm yetarli emas. Balans: {student_score.som}, kerak: {paid_amount}."}, status=400)
                if payment_method == 'coin' and student_score.coin < paid_amount:
                    return Response({"detail": f"Tanga yetarli emas. Balans: {student_score.coin}, kerak: {paid_amount}."}, status=400)
                if payment_method == 'score' and student_score.score < paid_amount:
                    return Response({"detail": f"Ball yetarli emas. Balans: {student_score.score}, kerak: {paid_amount}."}, status=400)

                if payment_method == 'som':
                    student_score.som -= int(paid_amount)
                elif payment_method == 'coin':
                    student_score.coin -= int(paid_amount)
                else:
                    student_score.score -= int(paid_amount)
                student_score.save()
                remaining = {"som": student_score.som, "coin": student_score.coin, "score": student_score.score}

            # Tutor uchun balans ayirish tizimi yo'q — faqat xarid yoziladi
            purchase = BookPurchase.objects.create(
                user=request.user,
                book=book,
                quantity=quantity,
                payment_method=payment_method,
                paid_amount=paid_amount,
            )

        return Response({
            "detail":          "Kitob muvaffaqiyatli sotib olindi.",
            "purchase_id":     purchase.id,
            "book_name_uz":    book.name_uz,
            "book_name_ru":    book.name_ru,
            "quantity":        quantity,
            "unit_price":      unit_price,
            "paid_amount":     paid_amount,
            "payment_method":  payment_method,
            "purchased_at":    purchase.purchased_at.strftime("%d/%m/%Y %H:%M"),
            "remaining_balance": remaining,
            "file": book.file.url if book.file else None,
        }, status=201)

    def _serialize_purchase(self, p):
        book = p.book
        user = p.user
        user_role = getattr(user, 'role', None)

        full_name = None
        if user_role == 'student':
            profile = getattr(user, 'student_profile', None)
            full_name = getattr(profile, 'full_name', None)
        elif user_role in ('tutor', 'teacher'):
            profile = getattr(user, 'teacher_profile', None)
            full_name = getattr(profile, 'full_name', None)

        return {
            "purchase_id":    p.id,
            "purchased_at":   p.purchased_at.strftime("%d/%m/%Y %H:%M"),
            "payment_method": p.payment_method,
            "quantity":       p.quantity,
            "paid_amount":    float(p.paid_amount),
            "user": {
                "id":        user.id,
                "phone":     getattr(user, 'phone', None),
                "role":      user_role,
                "full_name": full_name,
            },
            "book": {
                "id":          book.id,
                "name_uz":     book.name_uz,
                "name_ru":     book.name_ru,
                "cover_image": book.cover_image.url if book.cover_image else None,
                "file":        book.file.url        if book.file        else None,
                "is_offline":  book.is_offline,
                "status":      book.status,
            },
        }
