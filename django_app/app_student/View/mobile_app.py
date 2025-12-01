from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.models import StudentScore, TopicProgress
from django_app.app_teacher.models import Topic, Chapter
from django_app.app_user.models import  Subject_Category
from datetime import datetime, timedelta
from django.utils import timezone



class StudentRatingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Student profilini olamiz
        if not hasattr(user, "student_profile"):
            return Response({"error": "Faqat talaba reytingni ko‘ra oladi"}, status=403)

        student = user.student_profile   # ❗ TO‘G‘RI

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
                    "full_name": sc.student.full_name,
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

        # student_profile borligini tekshirish
        if not hasattr(user, "student_profile"):
            return Response({"error": "Faqat talaba uchun statistikalar mavjud"}, status=403)

        student = user.student_profile   # ❗ TO‘G‘RI

        today = timezone.now().date()
        monday = today - timedelta(days=today.weekday())

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



class StudentTopAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        type_value = request.data.get("type")       # score / coin / som
        top_count = request.data.get("top_count")   # integer

        # -------- 1) Validatsiya --------
        if type_value not in ["score", "coin", "som"]:
            return Response(
                {"error": "type faqat 'score', 'coin' yoki 'som' bo‘lishi kerak"},
                status=400
            )

        try:
            top_count = int(top_count)
        except:
            return Response({"error": "top_count butun son bo‘lishi kerak"}, status=400)

        # -------- 2) Dinamik tartiblash --------
        ordering_field = f"-{type_value}"   # masalan "-score"

        students = (
            StudentScore.objects
            .select_related("student", "student__user")
            .order_by(ordering_field)[:top_count]
        )

        # -------- 3) JSON formatlash --------
        data = []
        for item in students:
            data.append({
                "student_id": item.student.id,
                "full_name": item.student.user.full_name,
                "phone": item.student.user.phone,
                "score": item.score,
                "coin": item.coin,
                "som": item.som,
            })

        return Response({
            "type": type_value,
            "top_count": top_count,
            "results": data
        })
    

class SubjectProgressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Faqat talaba bo‘lsin
        if not hasattr(user, "student_profile"):
            return Response(
                {"detail": "Faqat talaba uchun ma'lumot mavjud."},
                status=403
            )

        student = user.student_profile

        categories = Subject_Category.objects.all()
        response_data = []

        for category in categories:
            # Shu bo‘limga tegishli barcha fanlar
            subjects = category.subjects.all()
            subject_count = subjects.count()

            # Agar bo‘limda fan bo‘lmasa, bo‘sh statistikani qaytaramiz
            if subject_count == 0:
                response_data.append({
                    "name": category.name,
                    "subject_count": 0,
                    "total_chapter_count": 0,
                    "total_topic_count": 0,
                    "total_present": 0.0,
                })
                continue

            # Shu bo‘limdagi barcha boblar va mavzular
            chapters = Chapter.objects.filter(subject__in=subjects)
            topics = Topic.objects.filter(chapter__in=chapters)

            total_chapter_count = chapters.count()
            total_topic_count = topics.count()

            # Studentning shu bo‘limdagi 80%+ o‘zlashtirgan mavzulari
            mastered_topics_qs = TopicProgress.objects.filter(
                user=student,
                topic__in=topics,
                score__gte=80
            ).values("topic").distinct()

            mastered_count = mastered_topics_qs.count()

            if total_topic_count > 0:
                total_present = round((mastered_count / total_topic_count) * 100, 1)
            else:
                total_present = 0.0

            # Natija
            response_data.append({
                "name": category.name,
                "subject_count": subject_count,
                "total_chapter_count": total_chapter_count,
                "total_topic_count": total_topic_count,
                "total_present": total_present,
            })

        return Response(response_data, status=200)