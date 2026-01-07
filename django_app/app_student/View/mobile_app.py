from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.models import StudentScore, TopicProgress
from django_app.app_teacher.models import Topic, Chapter
from django_app.app_user.models import  Subject_Category
from datetime import datetime, timedelta, date
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


import pytz

WEEK_DAY_MAP = {
    0: "mon",
    1: "tue",
    2: "wed",
    3: "thu",
    4: "fri",
    5: "sat",
    6: "sun",
}

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
        
        # GET parametrlarini olish
        year_param = request.GET.get('year')
        month_param = request.GET.get('month')
        week_param = request.GET.get('week')
        
        # Agar parametrlar berilgan bo'lsa, berilgan haftani ko'rsatamiz
        if year_param and month_param:
            try:
                year = int(year_param)
                month = int(month_param)
                
                # Oyning birinchi kuni
                first_day_of_month = date(year, month, 1)
                
                # Agar hafta parametri berilgan bo'lsa
                if week_param:
                    week_num = int(week_param)
                    # Haftani hisoblash
                    # Birinchi dushanbani topamiz
                    first_monday = first_day_of_month - timedelta(days=first_day_of_month.weekday())
                    # Berilgan haftaning dushanbasi
                    target_monday = first_monday + timedelta(weeks=week_num - 1)
                    target_sunday = target_monday + timedelta(days=6)
                    
                    # Agar haftaning ba'zi kunlari oldingi oyda bo'lsa
                    if target_monday.month != month:
                        target_monday = first_day_of_month
                    
                    # Agar haftaning ba'zi kunlari keyingi oyda bo'lsa
                    last_day_of_month = (first_day_of_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                    if target_sunday.month != month:
                        target_sunday = last_day_of_month
                    
                    week_start = target_monday
                    week_end = target_sunday
                else:
                    # Agar hafta berilmagan bo'lsa, oyning birinchi haftasini ko'rsatamiz
                    week_start = first_day_of_month - timedelta(days=first_day_of_month.weekday())
                    if week_start.month != month:
                        week_start = first_day_of_month
                    
                    week_end = week_start + timedelta(days=6)
                    last_day_of_month = (first_day_of_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                    if week_end.month != month:
                        week_end = last_day_of_month
                    
            except (ValueError, TypeError):
                # Agar parametrlarda xatolik bo'lsa, joriy haftani ko'rsatamiz
                week_start = today - timedelta(days=today.weekday())
                week_end = week_start + timedelta(days=6)
        else:
            # Hech qanday parametr berilmagan bo'lsa, joriy haftani ko'rsatamiz
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)

        # Hafta statistikasini tayyorlash
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

        # Ma'lumotlarni bazadan olish
        progresses = (
            TopicProgress.objects
            .select_related("topic__chapter__subject")
            .filter(
                user=student,
                completed_at__date__gte=week_start,
                completed_at__date__lte=week_end
            )
        )

        for prog in progresses:
            completed_local = prog.completed_at.astimezone(tz)
            day_key = WEEK_DAY_MAP[completed_local.weekday()]

            week_stats[day_key] = True

            topic = prog.topic
            chapter = topic.chapter
            subject = chapter.subject
            class_name = subject.classes.name

            week_details[day_key].append({
                "subject": {
                    "class_name_uz": f"{class_name}-sinf",
                    "class_name_ru": f"{class_name}-класс",
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

        # false bo'lgan kunlar uchun message
        for day, status in week_stats.items():
            if not status:
                week_details[day] = "siz mavzu ishlamagansiz"

        # Hafta haqida qo'shimcha ma'lumot
        week_info = {
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "current_week": (week_start <= today <= week_end),
            "year": week_start.year,
            "month": week_start.month,
            "week_number": self.get_week_number(week_start)
        }

        return Response({
            "week_info": week_info,
            "week_stats": week_stats,
            "details": week_details
        })
    
    def get_week_number(self, date_obj):
        """Oy ichidagi hafta raqamini hisoblaydi"""
        first_day = date(date_obj.year, date_obj.month, 1)
        # Oyning birinchi dushanbasi
        first_monday = first_day - timedelta(days=first_day.weekday())
        
        # Berilgan kun nechanchi haftada ekanligini hisoblaymiz
        week_number = ((date_obj - first_monday).days // 7) + 1
        
        return week_number


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
                "id": category.id,
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
