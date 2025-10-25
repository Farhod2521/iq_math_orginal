from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django_app.app_student.models import StudentScore, ConversionHistory


class ConvertView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        convert_type = request.data.get("type")
        amount = request.data.get("amount")  # foydalanuvchi kiritgan miqdor (int)

        if not convert_type or amount is None:
            return Response({"error": "type va amount kiritilishi shart."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = int(amount)
            if amount <= 0:
                return Response({"error": "Miqdor musbat son bo‘lishi kerak."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({"error": "Miqdor butun son bo‘lishi kerak."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student_score = StudentScore.objects.get(student__user=request.user)
        except StudentScore.DoesNotExist:
            return Response({"error": "Talaba topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        # 🔹 1. Ball → Tanga
        if convert_type == "SCORE_TO_COIN":
            required_score = amount * 15
            if student_score.score < required_score:
                return Response({"error": f"Sizda yetarli ball yo‘q. Kamida {required_score} ball kerak."}, status=status.HTTP_400_BAD_REQUEST)

            student_score.score -= required_score
            student_score.coin += amount
            student_score.save()

            ConversionHistory.objects.create(
                student=student_score.student,
                conversion_type="SCORE_TO_COIN",
                amount_from=required_score,
                amount_to=amount,
            )

            return Response({
                "message": f"{required_score} ball {amount} tangaga almashtirildi.",
                "coin": student_score.coin,
                "score": student_score.score
            }, status=status.HTTP_200_OK)

        # 🔹 2. Ball → So‘m
        elif convert_type == "SCORE_TO_SOM":
            required_score = amount  # foydalanuvchi nechta ballni o‘tkazmoqchi
            if student_score.score < required_score:
                return Response({"error": f"Sizda {required_score} ball yo‘q."}, status=status.HTTP_400_BAD_REQUEST)

            som = required_score // 15 * 100  # har 15 ball = 100 so‘m
            if som == 0:
                return Response({"error": "Konvertatsiya uchun kamida 15 ball kerak."}, status=status.HTTP_400_BAD_REQUEST)

            student_score.score -= (required_score // 15) * 15
            student_score.som = getattr(student_score, "som", 0) + som
            student_score.save()

            ConversionHistory.objects.create(
                student=student_score.student,
                conversion_type="SCORE_TO_SOM",
                amount_from=(required_score // 15) * 15,
                amount_to=som,
            )

            return Response({
                "message": f"{(required_score // 15) * 15} ball {som} so‘mga almashtirildi.",
                "score": student_score.score,
                "som": student_score.som
            }, status=status.HTTP_200_OK)

        # 🔹 3. Tanga → So‘m
        elif convert_type == "COIN_TO_SOM":
            if student_score.coin < amount:
                return Response({"error": f"Sizda {amount} tanga yo‘q."}, status=status.HTTP_400_BAD_REQUEST)

            som = amount * 100
            student_score.coin -= amount
            student_score.som = getattr(student_score, "som", 0) + som
            student_score.save()

            ConversionHistory.objects.create(
                student=student_score.student,
                conversion_type="COIN_TO_SOM",
                amount_from=amount,
                amount_to=som,
            )

            return Response({
                "message": f"{amount} tanga {som} so‘mga almashtirildi.",
                "coin": student_score.coin,
                "som": student_score.som
            }, status=status.HTTP_200_OK)

        else:
            return Response({"error": "Konvertatsiya turi noto‘g‘ri."}, status=status.HTTP_400_BAD_REQUEST)
