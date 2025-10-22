from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django_app.app_student.models import StudentScore, ConversionHistory
class ConvertView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        convert_type = request.data.get("type")

        try:
            student_score = StudentScore.objects.get(student__user=request.user)
        except StudentScore.DoesNotExist:
            return Response({"error": "Talaba topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        if convert_type == "SCORE_TO_COIN":
            # Har 15 ball = 1 tanga
            if student_score.score < 15:
                return Response({"error": "Konvertatsiya uchun kamida 15 ball kerak."}, status=status.HTTP_400_BAD_REQUEST)
            
            tangalar = student_score.score // 15
            qolgan_ball = student_score.score % 15

            student_score.coin += tangalar
            student_score.score = qolgan_ball
            student_score.save()

            ConversionHistory.objects.create(
                student=student_score.student,
                conversion_type="SCORE_TO_COIN",
                amount_from=tangalar * 15,
                amount_to=tangalar,
            )

            return Response({
                "message": f"{tangalar * 15} ball {tangalar} tangaga almashtirildi.",
                "coin": student_score.coin,
                "score": student_score.score
            }, status=status.HTTP_200_OK)

        elif convert_type == "COIN_TO_SOM":
            # Har 1 tanga = 100 so‘m
            if student_score.coin < 1:
                return Response({"error": "Konvertatsiya uchun kamida 1 tanga kerak."}, status=status.HTTP_400_BAD_REQUEST)
            
            som = student_score.coin * 100
            student_score.som += som
            student_score.coin = 0  # hammasini so‘mga o‘tkazdik
            student_score.save()

            ConversionHistory.objects.create(
                student=student_score.student,
                conversion_type="COIN_TO_SOM",
                amount_from=som // 100,  # tanga soni
                amount_to=som,  # so‘m
            )

            return Response({
                "message": f"{som // 100} tanga {som} so‘mga almashtirildi.",
                "som": student_score.som,
                "coin": student_score.coin
            }, status=status.HTTP_200_OK)

        else:
            return Response({"error": "Konvertatsiya turi noto‘g‘ri."}, status=status.HTTP_400_BAD_REQUEST)