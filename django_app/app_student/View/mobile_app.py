from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.models import StudentScore, TopicProgress
from django_app.app_teacher.models import Topic, Chapter
from django_app.app_user.models import  Subject_Category
from datetime import datetime, timedelta
from django.utils import timezone
from django_app.app_student.serializers import SubjectCategoryDetailSerializer
from django.db.models import Count
from rest_framework import status
class StudentRatingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Student profilini olamiz
        if not hasattr(user, "student_profile"):
            return Response({"error": "Faqat talaba reytingni ko‘ra oladi"}, status=403)

        student = user.student_profile

        # StudentScore obj — bo‘lmasa yangi bo‘sh obyekt yaratamiz
        my_score, _ = StudentScore.objects.get_or_create(
            student=student,
            defaults={"score": 0, "coin": 0, "som": 0}
        )

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
    0: "mon",
    1: "tue",
    2: "wed",
    3: "thu",
    4: "fri",
    5: "sat",
    6: "sun",
}
import pytz
class WeeklyStudyStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if not hasattr(user, "student_profile"):
            return Response(
                {"error": "Faqat talaba uchun statistikalar mavjud"},
                status=403
            )

        student = user.student_profile

        tz = pytz.timezone("Asia/Tashkent")
        now = timezone.now().astimezone(tz)
        today = now.date()
        monday = today - timedelta(days=today.weekday())

        week_stats = {
            "mon": False,
            "tue": False,
            "wed": False,
            "thu": False,
            "fri": False,
            "sat": False,
            "sun": False,
        }

        week_details = {
            "mon": [],
            "tue": [],
            "wed": [],
            "thu": [],
            "fri": [],
            "sat": [],
            "sun": [],
        }

        progresses = (
            TopicProgress.objects
            .select_related("topic__chapter__subject")
            .filter(
                user=student,
                completed_at__date__gte=monday,
                completed_at__date__lte=today
            )
        )

        for prog in progresses:
            completed_local = prog.completed_at.astimezone(tz)
            day_key = WEEK_DAY_MAP[completed_local.weekday()]

            week_stats[day_key] = True

            topic = prog.topic
            chapter = topic.chapter
            subject = chapter.subject

            week_details[day_key].append({
                "subject": {
                    "name_uz": subject.name_uz,
                    "name_ru": subject.name_ru,
                },
                "chapter": {
                    "name_uz": chapter.name_uz,
                    "name_ru": chapter.name_ru,
                },
                "topic": {
                    "name_uz": topic.name_uz,
                    "name_ru": topic.name_ru,
                },
                "score": prog.score
            })

        # false bo‘lgan kunlar uchun message
        for day, status in week_stats.items():
            if not status:
                week_details[day] = "siz mavzu ishlamagansiz"

        return Response({
            "week_stats": week_stats,
            "details": week_details
        })





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
                "full_name": item.student.full_name,
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
                "name_uz": category.name_uz,
                "name_ru": category.name_ru,
                "subject_count": subject_count,
                "total_chapter_count": total_chapter_count,
                "total_topic_count": total_topic_count,
                "total_present": total_present,
            })

        return Response(response_data, status=200)
    


class SubjectCategoryDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        category_id = request.data.get("category_id")

        if not category_id:
            return Response(
                {"error": "category_id majburiy"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            category = (
                Subject_Category.objects
                .annotate(subjects_count=Count("subjects", distinct=True))
                .get(id=category_id)
            )
        except Subject_Category.DoesNotExist:
            return Response(
                {"error": "Fan bo‘limi topilmadi"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SubjectCategoryDetailSerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)
