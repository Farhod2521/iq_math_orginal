from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import Category, Tag, Book
from .serializers import CategorySerializer, TagSerializer, BookReadSerializer, BookWriteSerializer


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
