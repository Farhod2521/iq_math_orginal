from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from  django_app.app_teacher.models import Topic, Chapter
from  django_app.app_student.models  import TopicProgress
from rest_framework.permissions import IsAuthenticated






class StudentNextTopicAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 🔒 Faqat student kirishi mumkin
        if not hasattr(user, 'student_profile'):
            return Response({"detail": "Faqat o‘quvchilar uchun."}, status=status.HTTP_403_FORBIDDEN)

        student = user.student_profile

        # 🧮 1️⃣ Talabaning ishlagan barcha mavzulari
        progresses = TopicProgress.objects.filter(user=student).select_related(
            "topic", "topic__chapter", "topic__chapter__subject"
        )

        if progresses.exists():
            # 🎯 Har bir fan uchun eng oxirgi ishlangan mavzuni topamiz
            subjects = {}
            for progress in progresses.order_by('-completed_at', '-id'):  # ✅ to‘g‘rilangan joy
                topic = progress.topic
                subject = topic.chapter.subject

                # Agar bu fan uchun hali tanlanmagan bo‘lsa — birinchi topilganini olamiz (ya’ni eng oxirgi ishlangan)
                if subject.id not in subjects:
                    subjects[subject.id] = topic

            # 🔚 Har bir fan uchun eng oxirgi ishlangan mavzu → endi o‘sha fandan keyingi mavzuni topamiz
            results = []
            for subject_id, last_topic in subjects.items():
                chapter_topics = list(Topic.objects.filter(chapter=last_topic.chapter).order_by('order'))
                try:
                    current_index = chapter_topics.index(last_topic)
                    # Agar bu chapterdagi oxirgi mavzu bo‘lsa → keyingi chapterdan boshlaymiz
                    if current_index == len(chapter_topics) - 1:
                        next_chapter = Chapter.objects.filter(
                            subject=last_topic.chapter.subject,
                            order__gt=last_topic.chapter.order
                        ).order_by('order').first()
                        if next_chapter:
                            next_topic = Topic.objects.filter(chapter=next_chapter).order_by('order').first()
                        else:
                            next_topic = None
                    else:
                        next_topic = chapter_topics[current_index + 1]
                except ValueError:
                    next_topic = None

                if next_topic:
                    results.append({
                        "subject": last_topic.chapter.subject.name_uz,
                        "chapter": next_topic.chapter.name_uz,
                        "topic": next_topic.name_uz,
                        "score": 0,
                        "reminder": f"{last_topic.chapter.subject.name_uz} fanidan '{next_topic.name_uz}' mavzusini bajarish kerak!"
                    })

            # ✅ Agar kamida bitta fan uchun mavjud bo‘lsa
            if results:
                return Response(results, status=status.HTTP_200_OK)

        # 2️⃣ Agar hech qaysi mavzu ishlanmagan bo‘lsa — ro‘yxatdan o‘tgan fani bo‘yicha birinchi mavzuni ko‘rsatamiz
        if student.class_name:
            subject = student.class_name
            first_chapter = Chapter.objects.filter(subject=subject).order_by('order').first()
            if first_chapter:
                first_topic = Topic.objects.filter(chapter=first_chapter).order_by('order').first()
                if first_topic:
                    return Response({
                        "subject": subject.name_uz,
                        "chapter": first_chapter.name_uz,
                        "topic": first_topic.name_uz,
                        "score": 0,
                        "reminder": f"{subject.name_uz} fanidan '{first_topic.name_uz}' mavzusini boshlang!"
                    }, status=status.HTTP_200_OK)

        # 3️⃣ Aks holda hech narsa yo‘q
        return Response({"detail": "Hozircha hech qanday mavzu mavjud emas."}, status=status.HTTP_204_NO_CONTENT)


class StudentLastProgressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # ✅ Faqat student kirishi mumkin
        if not hasattr(user, 'student_profile'):
            return Response({"detail": "Faqat o‘quvchilar uchun."}, status=status.HTTP_403_FORBIDDEN)

        student = user.student_profile

        # 🔍 Eng oxirgi ishlangan mavzuni olish
        last_progress = (
            TopicProgress.objects
            .filter(user=student)
            .select_related('topic', 'topic__chapter', 'topic__chapter__subject')
            .order_by('-completed_at')
            .first()
        )

        if not last_progress:
            return Response({"detail": "Hali hech qanday mavzu ishlanmagan."}, status=status.HTTP_204_NO_CONTENT)

        topic = last_progress.topic
        subject = topic.chapter.subject

        data = {
            "subject_name_uz": subject.name_uz,
            "topic_name_uz": topic.name_uz,
            "score": round(last_progress.score, 1),
            "completed_at": last_progress.completed_at.strftime("%d/%m/%Y %H:%M") if last_progress.completed_at else None
        }

        return Response(data, status=status.HTTP_200_OK)