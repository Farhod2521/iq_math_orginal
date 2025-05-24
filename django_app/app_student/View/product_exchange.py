from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django_app.app_management.models import Product
from django_app.app_user.models import Student
from ..models import StudentScore, ProductExchange

class ProductExchangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, product_id):
        user = request.user

        # faqat student
        if user.role != 'student':
            return Response({'error': 'Faqat talaba roliga ruxsat berilgan.'}, status=403)

        # student profile va score topiladi
        try:
            student = user.student_profile
        except Student.DoesNotExist:
            return Response({'error': 'Student topilmadi.'}, status=404)

        student_score = StudentScore.objects.filter(student=student).first()
        if not student_score:
            return Response({'error': 'Ball mavjud emas.'}, status=404)

        # mahsulot topiladi
        product = get_object_or_404(Product, id=product_id)

        # ball yetarlimi
        if student_score.score < product.ball:
            return Response({'error': f"Sizda yetarli ball yo'q. Kerakli: {product.ball}, Sizda: {student_score.score}"}, status=400)

        # ballni ayirish va yozib qo‘yish
        student_score.score -= product.ball
        student_score.save()

        exchange = ProductExchange.objects.create(
            student=student,
            product=product,
            used_score=product.ball,
            status='approved'  # yoki 'pending', agar admin tasdiqlash kerak bo‘lsa
        )

        return Response({
            'message': f"{product.name} mahsuloti muvaffaqiyatli olindi.",
            'remaining_score': student_score.score,
            'exchange_id': exchange.id,
            'status': exchange.status,
        })
