from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django_app.app_student.models import StudentScore, ConversionHistory
from django_app.app_management.models import ConversionRate


class ConvertView(APIView):
    """
    Ball → Tanga → So'm konvertatsiya tizimi
    Kurs: ConversionRate modelidan o'qiladi (hardcoded emas)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        convert_type = request.data.get("type")
        amount = request.data.get("amount")

        if not convert_type or amount is None:
            return Response(
                {"error": "type va amount kiritilishi shart."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount = int(amount)
            if amount <= 0:
                return Response(
                    {"error": "Miqdor musbat son bo'lishi kerak."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {"error": "Miqdor butun son bo'lishi kerak."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Kursni bazadan o'qiymiz
        rate = ConversionRate.objects.last()
        if not rate:
            return Response(
                {"error": "Konversiya kursi sozlanmagan. Admin bilan bog'laning."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            student_score = StudentScore.objects.get(student__user=request.user)
        except StudentScore.DoesNotExist:
            return Response({"error": "Talaba topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        # coin_to_score: 1 tangaga necha ball kerak
        # coin_to_money: 1 tanga necha so'mga teng

        if convert_type == "SCORE_TO_COIN":
            # amount = nechta tanga olmoqchi
            required_score = amount * rate.coin_to_score
            if student_score.score < required_score:
                return Response(
                    {"error": f"Yetarli ball yo'q. {amount} tanga uchun {required_score} ball kerak, sizda {student_score.score} ball bor."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            student_score.score -= required_score
            student_score.coin += amount
            student_score.save()

            ConversionHistory.objects.create(
                student=student_score.student,
                conversion_type="SCORE_TO_COIN",
                amount_from=required_score,
                amount_to=amount,
                som_after=student_score.som,
                status="approved"
            )

            return Response({
                "message": f"{required_score} ball → {amount} tanga",
                "score": student_score.score,
                "coin": student_score.coin,
                "som": student_score.som
            }, status=status.HTTP_200_OK)

        elif convert_type == "SCORE_TO_SOM":
            # amount = nechta ball sarflamoqchi
            if student_score.score < amount:
                return Response(
                    {"error": f"Yetarli ball yo'q. Sizda {student_score.score} ball bor."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Faqat to'liq tangaga aylantiriluvchi ballni hisoblaymiz
            coins = amount // rate.coin_to_score
            if coins == 0:
                return Response(
                    {"error": f"Kamida {rate.coin_to_score} ball kerak."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            used_score = coins * rate.coin_to_score
            som = int(coins * rate.coin_to_money)

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
                "message": f"{used_score} ball → {som} so'm",
                "score": student_score.score,
                "som": student_score.som
            }, status=status.HTTP_200_OK)

        elif convert_type == "COIN_TO_SOM":
            # amount = nechta tanga sarflamoqchi
            if student_score.coin < amount:
                return Response(
                    {"error": f"Yetarli tanga yo'q. Sizda {student_score.coin} tanga bor."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            som = int(amount * rate.coin_to_money)
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
                "message": f"{amount} tanga → {som} so'm",
                "coin": student_score.coin,
                "som": student_score.som
            }, status=status.HTTP_200_OK)

        else:
            return Response(
                {"error": "Konvertatsiya turi noto'g'ri. SCORE_TO_COIN | SCORE_TO_SOM | COIN_TO_SOM"},
                status=status.HTTP_400_BAD_REQUEST
            )
