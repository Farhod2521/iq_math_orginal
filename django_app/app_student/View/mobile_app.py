from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.models import StudentScore, TopicProgress
from datetime import datetime, timedelta
from django.utils import timezone



class StudentRatingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Student profilini olamiz
        if not hasattr(user, "student"):
            return Response({"error": "Faqat talaba reytingni ko‘ra oladi"}, status=403)

        student = user.student

        # StudentScore obj
        try:
            my_score = StudentScore.objects.get(student=student)
        except StudentScore.DoesNotExist:
            return Response({"error": "Talabaning reytingi mavjud emas"}, status=404)

        # Barcha reytinglar
        all_scores = StudentScore.objects.all()

        # --- TOP 3 ni olish funksiyasi ---
        def top_3_list(field):
            top = all_scores.order_by(f"-{field}")[:3]
            return [
                {
                    "full_name": sc.student.user.full_name,
                    field: getattr(sc, field)
                }
                for sc in top
            ]

        # --- Mening o‘rnim ---
        def my_rank(field):
            value = getattr(my_score, field)
            return all_scores.filter(**{f"{field}__gt": value}).count() + 1

        data = {
            "score": {
                "top_3": top_3_list("score"),
                "my_rank": my_rank("score"),
                "my_value": my_score.score
            },
            "coin": {
                "top_3": top_3_list("coin"),
                "my_rank": my_rank("coin"),
                "my_value": my_score.coin
            },
            "som": {
                "top_3": top_3_list("som"),
                "my_rank": my_rank("som"),
                "my_value": my_score.som
            }
        }

        return Response(data, status=200)




WEEK_DAY_MAP = {
    0: "mon",   # Monday
    1: "tue",   # Tuesday
    2: "wed",   # Wednesday
    3: "thu",   # Thursday
    4: "fri",   # Friday
    5: "sat",   # Saturday
    6: "sun",   # Sunday
}
class WeeklyStudyStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if not hasattr(user, "student"):
            return Response({"error": "Faqat talaba uchun statistikalar mavjud"}, status=403)

        student = user.student

        today = timezone.now().date()
        monday = today - timedelta(days=today.weekday())   # haftaning boshini topish

        # boshida hamma kunlar false
        week_stats = {
            "mon": False,
            "tue": False,
            "wed": False,
            "thu": False,
            "fri": False,
            "sat": False,
            "sun": False,
        }

        # Dushanbadan hozirgacha bo'lgan progresslar
        progresses = TopicProgress.objects.filter(
            user=student,
            completed_at__date__gte=monday,
            completed_at__date__lte=today
        )

        for prog in progresses:
            if prog.completed_at:
                weekday_int = prog.completed_at.weekday()  # 0–6
                day_key = WEEK_DAY_MAP[weekday_int]
                week_stats[day_key] = True

        return Response({"week_stats": week_stats})
