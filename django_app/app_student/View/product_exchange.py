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
            return Response({
                'error_uz': 'Faqat talaba roliga ruxsat berilgan.',
                'error_ru': 'Доступ разрешен только студентам.'
            }, status=403)

        # student profile va score topiladi
        try:
            student = user.student_profile
        except Student.DoesNotExist:
            return Response({
                'error_uz': 'Talaba profili topilmadi.',
                'error_ru': 'Профиль студента не найден.'
            }, status=404)

        student_score = StudentScore.objects.filter(student=student).first()
        if not student_score:
            return Response({
                'error_uz': 'Sizda ball mavjud emas.',
                'error_ru': 'У вас нет баллов.'
            }, status=404)

        # mahsulot topiladi
        product = get_object_or_404(Product, id=product_id)

        # ball yetarlimi
        if student_score.score < product.ball:
            return Response({
                'error_uz': f"Sizda yetarli ball yo'q. Kerakli: {product.ball}, Sizda: {student_score.score}",
                'error_ru': f"У вас недостаточно баллов. Необходимо: {product.ball}, У вас: {student_score.score}"
            }, status=400)

        # ballni ayirish va yozib qo‘yish
        student_score.score -= product.ball
        student_score.save()

        exchange = ProductExchange.objects.create(
            student=student,
            product=product,
            used_score=product.ball,
            status='approved'
        )

        return Response({
            'message_uz': f"{product.name} mahsuloti muvaffaqiyatli olindi.",
            'message_ru': f"Товар {product.name} успешно получен.",
            'remaining_score': student_score.score,
            'exchange_id': exchange.id,
            'status': exchange.status,
        })



class ProductExchangeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != 'student':
            return Response({
                'error_uz': 'Faqat talaba roliga ruxsat berilgan.',
                'error_ru': 'Доступ разрешен только студентам.'
            }, status=403)

        try:
            student = user.student_profile
        except Student.DoesNotExist:
            return Response({
                'error_uz': 'Talaba profili topilmadi.',
                'error_ru': 'Профиль студента не найден.'
            }, status=404)

        exchanges = student.product_exchanges.all().order_by('-created_at')

        data = []
        for exchange in exchanges:
            data.append({
                'product_name': exchange.product.name,
                'used_score': exchange.used_score,
                'status': exchange.status,
                'created_at': exchange.created_at.strftime('%Y-%m-%d %H:%M'),
            })

        return Response({
            'exchanges': data
        })