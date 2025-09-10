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

        student_score = StudentScore.objects.filter(student=student).first()
        if not student_score:
            return Response({
                'error_uz': 'Sizda coin mavjud emas.',
                'error_ru': 'У вас нет монет.'
            }, status=404)

        product = get_object_or_404(Product, id=product_id)

        if student_score.coin < product.coin:
            return Response({
                'error_uz': f"Sizda yetarli coin yo'q. Kerakli: {product.coin}, Sizda: {student_score.coin}",
                'error_ru': f"У вас недостаточно монет. Необходимо: {product.coin}, У вас: {student_score.coin}"
            }, status=400)

        student_score.coin -= product.coin
        student_score.save()

        exchange = ProductExchange.objects.create(
            student=student,
            product=product,
            used_coin=product.coin,  # modelda hali used_score deb turgan bo‘lsa, nomi o‘zgartirilmagan
            status='approved'
        )

        return Response({
            'message_uz': f"{product.name} mahsuloti muvaffaqiyatli olindi.",
            'message_ru': f"Товар {product.name} успешно получен.",
            'remaining_coin': student_score.coin,
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
                'used_coin': exchange.used_coin,  # modeldagi field nomi hali used_score deb turgan bo‘lsa
                'status': exchange.status,
                'created_at': exchange.created_at.strftime('%Y-%m-%d %H:%M'),
            })

        return Response({
            'message_uz': 'Siz almashtirgan mahsulotlar ro‘yxati.',
            'message_ru': 'Список обменянных вами товаров.',
            'exchanges': data
        })
