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

DAY_NAME_MAP = {
    "mon": {"uz": "Dushanba", "ru": "Понедельник"},
    "tue": {"uz": "Seshanba", "ru": "Вторник"},
    "wed": {"uz": "Chorshanba", "ru": "Среда"},
    "thu": {"uz": "Payshanba", "ru": "Четверг"},
    "fri": {"uz": "Juma", "ru": "Пятница"},
    "sat": {"uz": "Shanba", "ru": "Суббота"},
    "sun": {"uz": "Yakshanba", "ru": "Воскресенье"},
}

class WeeklyStudyStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get_week_range(self, year, month, week_num):
        """
        Berilgan yil, oy va hafta raqamiga ko'ra haftaning boshlanish va tugash kunlarini hisoblaydi
        """
        # Oyning birinchi kunini topamiz
        first_day_of_month = date(year, month, 1)
        
        # Oyning birinchi haftasining dushanbasini topamiz
        # Dushanba haftaning birinchi kuni deb hisoblaymiz
        first_monday = first_day_of_month - timedelta(days=first_day_of_month.weekday())
        
        # Berilgan haftaning dushanbasini hisoblaymiz
        target_monday = first_monday + timedelta(weeks=week_num - 1)
        target_sunday = target_monday + timedelta(days=6)
        
        # Agar haftaning ba'zi kunlari oldingi oyda bo'lsa, oyning birinchi kunidan boshlaymiz
        if target_monday.month != month:
            target_monday = first_day_of_month
            
        # Agar haftaning ba'zi kunlari keyingi oyda bo'lsa, oyning oxirgi kunida tugatamiz
        last_day_of_month = (first_day_of_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        if target_sunday.month != month:
            target_sunday = last_day_of_month
            
        return target_monday, target_sunday
    
    def get_month_calendar(self, year, month):
        """
        Oy kalendarini yaratadi - har bir hafta uchun kunlar ro'yxati
        """
        # Oyning birinchi va oxirgi kunlari
        first_day = date(year, month, 1)
        last_day = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        
        # Kalendar uchun bo'sh ro'yxat
        calendar = []
        
        # Hozirgi haftani boshlash
        current_week = []
        
        # Oyning birinchi kunigacha bo'sh joylar
        first_weekday = first_day.weekday()
        for _ in range(first_weekday):
            current_week.append(None)
        
        # Oyning barcha kunlarini qo'shamiz
        current_day = first_day
        while current_day <= last_day:
            current_week.append(current_day.day)
            
            # Agar hafta tugagan bo'lsa (yakshanba), yangi haftani boshlaymiz
            if current_day.weekday() == 6:
                calendar.append(current_week)
                current_week = []
            
            current_day += timedelta(days=1)
        
        # Oxirgi haftani to'ldiramiz
        if current_week:
            # Oxirgi haftani to'ldirish uchun bo'sh joylar
            while len(current_week) < 7:
                current_week.append(None)
            calendar.append(current_week)
        
        return calendar
    
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
        
        # GET parametrlarini olamiz
        year = request.GET.get('year')
        month = request.GET.get('month')
        week = request.GET.get('week')
        
        # Agar parametrlar berilmagan bo'lsa, joriy haftani ko'rsatamiz
        if not year or not month:
            year = today.year
            month = today.month
        
        # Oyni raqamga aylantiramiz
        try:
            year = int(year)
            month = int(month)
            
            # Oylarni o'tgan/kelgan oylarga o'tish imkoniyati
            if request.GET.get('prev_month'):
                month -= 1
                if month == 0:
                    month = 12
                    year -= 1
            elif request.GET.get('next_month'):
                month += 1
                if month == 13:
                    month = 1
                    year += 1
            
            # Haftani aniqlash
            if week:
                week_num = int(week)
                # Hafta raqamini tekshiramiz
                if week_num < 1:
                    week_num = 1
                elif week_num > 6:  # Bir oyda maksimum 6 hafta bo'lishi mumkin
                    week_num = 6
            else:
                # Agar hafta berilmagan bo'lsa, joriy haftani topamiz
                week_num = ((today - date(year, month, 1)).days // 7) + 1
                if week_num < 1:
                    week_num = 1
                elif week_num > 6:
                    week_num = 6
                
                # Agar joriy oy bo'lmasa, birinchi haftani ko'rsatamiz
                if today.year != year or today.month != month:
                    week_num = 1
            
            # Haftaning boshlanish va tugash kunlarini hisoblaymiz
            week_start, week_end = self.get_week_range(year, month, week_num)
            
            # Oy kalendarini tayyorlaymiz
            month_calendar = self.get_month_calendar(year, month)
            
            # Hozirgi haftaning kunlar ro'yxati
            week_dates = []
            current_date = week_start
            while current_date <= week_end:
                week_dates.append(current_date)
                current_date += timedelta(days=1)
            
        except (ValueError, TypeError) as e:
            # Agar parametrlarda xatolik bo'lsa, joriy haftani ko'rsatamiz
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            year = today.year
            month = today.month
            week_num = ((today - date(year, month, 1)).days // 7) + 1
            month_calendar = self.get_month_calendar(year, month)
            week_dates = [week_start + timedelta(days=i) for i in range(7)]

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
        
        # Ma'lumotlarni olish
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
                "score": prog.score,
                "completed_at": completed_local.strftime("%Y-%m-%d %H:%M")
            })

        # false bo'lgan kunlar uchun message
        for day, status in week_stats.items():
            if not status:
                week_details[day] = {
                    "message_uz": "Siz mavzu ishlamagansiz",
                    "message_ru": "Вы не изучали темы"
                }

        # Har bir kun uchun to'liq ma'lumot
        week_days_info = {}
        for i, day_date in enumerate(week_dates):
            day_key = WEEK_DAY_MAP[i]
            week_days_info[day_key] = {
                "date": day_date.strftime("%Y-%m-%d"),
                "day_name": DAY_NAME_MAP[day_key],
                "is_today": day_date == today,
                "is_current_month": day_date.month == month
            }

        return Response({
            "year": year,
            "month": month,
            "month_name_uz": self.get_month_name_uz(month),
            "month_name_ru": self.get_month_name_ru(month),
            "week_number": week_num,
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "month_calendar": month_calendar,
            "week_days": week_days_info,
            "week_stats": week_stats,
            "details": week_details,
            "navigation": {
                "prev_month": f"/api/study-stats/weekly/?year={year}&month={month-1 if month > 1 else 12}&week=1",
                "next_month": f"/api/study-stats/weekly/?year={year}&month={month+1 if month < 12 else 1}&week=1",
                "prev_week": f"/api/study-stats/weekly/?year={year}&month={month}&week={week_num-1 if week_num > 1 else 1}",
                "next_week": f"/api/study-stats/weekly/?year={year}&month={month}&week={week_num+1 if week_num < 6 else 6}",
                "current_week": f"/api/study-stats/weekly/"
            }
        })
    
    def get_month_name_uz(self, month):
        """O'zbekcha oy nomlari"""
        months = {
            1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
            5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
            9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr"
        }
        return months.get(month, "")
    
    def get_month_name_ru(self, month):
        """Ruscha oy nomlari"""
        months = {
            1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
            5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
            9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
        }
        return months.get(month, "")




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
