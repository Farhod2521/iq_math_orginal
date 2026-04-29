from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django_app.app_management.models import Product
from django_app.app_user.models import Student
from ..models import StudentScore, ProductExchange
from django.utils import timezone
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

        # 🔹 Mahsulot sonini tekshirish
        if product.count <= 0:
            return Response({
                'error_uz': 'Bu mahsulot qolmagan.',
                'error_ru': 'Этот товар закончился.'
            }, status=400)

        # 🔹 Coin yetarliligini tekshirish
        if student_score.coin < product.coin:
            return Response({
                'error_uz': f"Sizda yetarli coin yo'q. Kerakli: {product.coin}, Sizda: {student_score.coin}",
                'error_ru': f"У вас недостаточно монет. Необходимо: {product.coin}, У вас: {student_score.coin}"
            }, status=400)

        # 🔹 Coinni kamaytirish
        student_score.coin -= product.coin
        student_score.save()

        # 🔹 Mahsulot sonini kamaytirish
        product.count -= 1
        product.save()

        # 🔹 Yangi almashinuv yozuvini yaratish
        exchange = ProductExchange.objects.create(
            student=student,
            product=product,
            used_coin=product.coin,
            delivery_status="new"
        )

        return Response({
            'message_uz': f"{product.name} mahsuloti muvaffaqiyatli olindi.",
            'message_ru': f"Товар {product.name} успешно получен.",
            'remaining_coin': student_score.coin,
            'product_count': product.count,
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
            product_image_url = (
                request.build_absolute_uri(exchange.product.image.url)
                if exchange.product.image
                else None
            )
            data.append({
                'product_name': exchange.product.name,
                'product_image': product_image_url,
                'used_coin': exchange.used_coin,
                'delivery_status': exchange.delivery_status,
                'is_confirmed_by_student': exchange.is_confirmed_by_student,
                'created_at': exchange.created_at.strftime('%Y-%m-%d %H:%M'),
            })

        return Response({
            'message_uz': 'Siz almashtirgan mahsulotlar ro‘yxati.',
            'message_ru': 'Список обменянных вами товаров.',
            'exchanges': data
        })
    


class ProductExchangeConfirmAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            exchange = ProductExchange.objects.get(id=pk, student=request.user.student_profile)
        except:
            return Response({"error": "Almashinuv topilmadi"}, status=404)

        if exchange.delivery_status != "delivered":
            return Response({"error": "Tovar hali yetkazilmagan!"}, status=400)

        exchange.delivery_status = "confirmed"
        exchange.is_confirmed_by_student = True
        exchange.confirmed_at = timezone.now()
        exchange.save()

        return Response({
            "message_uz": "Hizmatimizdan foydalanganingiz uchun rahmat!",
            "message_ru": "Спасибо, что воспользовались нашим сервисом!",
            "status": exchange.delivery_status,
        })