from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django_app.app_student.models import StudentScore, ConversionHistory


class ConvertView(APIView):
    """
    Ball → Tanga → So‘m konvertatsiya tizimi
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        convert_type = request.data.get("type")
        amount = request.data.get("amount")  # foydalanuvchi kiritgan miqdor (int)

        # 🔹 1. Kiritilgan ma'lumotlarni tekshiramiz
        if not convert_type or amount is None:
            return Response(
                {"error": "type va amount kiritilishi shart."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount = int(amount)
            if amount <= 0:
                return Response(
                    {"error": "Miqdor musbat son bo‘lishi kerak."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {"error": "Miqdor butun son bo‘lishi kerak."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔹 2. Talabani topamiz
        try:
            student_score = StudentScore.objects.get(student__user=request.user)
        except StudentScore.DoesNotExist:
            return Response({"error": "Talaba topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        # 🔹 3. Konvertatsiya logikasi
        if convert_type == "SCORE_TO_COIN":
            # 15 ball = 1 tanga
            required_score = amount * 15
            if student_score.score < required_score:
                return Response(
                    {"error": f"Sizda yetarli ball yo‘q. Kamida {required_score} ball kerak."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # balanslarni o‘zgartirish
            student_score.score -= required_score
            student_score.coin += amount
            student_score.save()

            # tarixga yozish
            ConversionHistory.objects.create(
                student=student_score.student,
                conversion_type="SCORE_TO_COIN",
                amount_from=required_score,
                amount_to=amount,
                som_after=student_score.som,
                status="approved"
            )

            return Response({
                "message": f"{required_score} ball {amount} tangaga almashtirildi.",
                "score": student_score.score,
                "coin": student_score.coin,
                "som": student_score.som
            }, status=status.HTTP_200_OK)

        elif convert_type == "SCORE_TO_SOM":
            # Har 15 ball = 100 so‘m
            required_score = amount
            if student_score.score < required_score:
                return Response(
                    {"error": f"Sizda {required_score} ball yo‘q."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # konvertatsiya hisoblash
            som = (required_score // 15) * 100
            if som == 0:
                return Response(
                    {"error": "Konvertatsiya uchun kamida 15 ball kerak."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            used_score = (required_score // 15) * 15
            student_score.score -= used_score
            student_score.som += som
            student_score.save()

            ConversionHistory.objects.create(
                student=student_score.student,
                conversion_type="SCORE_TO_SOM",
                amount_from=used_score,
                amount_to=som,
                som_after=student_score.som,
                status="approved"
            )

            return Response({
                "message": f"{used_score} ball {som} so‘mga almashtirildi.",
                "score": student_score.score,
                "som": student_score.som
            }, status=status.HTTP_200_OK)

        elif convert_type == "COIN_TO_SOM":
            # 1 tanga = 100 so‘m
            if student_score.coin < amount:
                return Response(
                    {"error": f"Sizda {amount} tanga yo‘q."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            som = amount * 100
            student_score.coin -= amount
            student_score.som += som
            student_score.save()

            ConversionHistory.objects.create(
                student=student_score.student,
                conversion_type="COIN_TO_SOM",
                amount_from=amount,
                amount_to=som,
                som_after=student_score.som,
                status="approved"
            )

            return Response({
                "message": f"{amount} tanga {som} so‘mga almashtirildi.",
                "coin": student_score.coin,
                "som": student_score.som
            }, status=status.HTTP_200_OK)

        else:
            return Response(
                {"error": "Konvertatsiya turi noto‘g‘ri."},
                status=status.HTTP_400_BAD_REQUEST
            )