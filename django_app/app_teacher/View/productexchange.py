from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django_app.app_student.models import ProductExchange

from django_app.app_teacher.serializers import ProductExchangeSerializer


class ProductExchangeListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Faqat barcha yozuvlarni chiqarish (admin yoki umumiy ro‘yxat)
        exchanges = ProductExchange.objects.select_related('student', 'product').order_by('-created_at')
        serializer = ProductExchangeSerializer(exchanges, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)