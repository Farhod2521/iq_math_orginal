from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import Category, Tag, Book
from .serializers import CategorySerializer, TagSerializer, BookReadSerializer, BookWriteSerializer
from django_app.app_management.models import ConversionRate


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
