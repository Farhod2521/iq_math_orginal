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

        # 🧮 1️⃣ Talabaning ishlagan barcha mavzulari (completed_at bo‘yicha eng oxirgisi birinchi bo'ladi)
        progresses = TopicProgress.objects.filter(user=student).select_related(
            "topic", "topic__chapter", "topic__chapter__subject"
        ).order_by('-completed_at', '-id')

        # ⭐⭐⭐ YANGI QOIDA: faqat eng oxirgi ishlangan FANni olish ⭐⭐⭐
        if progresses.exists():
            last_progress = progresses.first()  # 👈 Eng oxirgi ishlangan progress
            last_topic = last_progress.topic
            subject = last_topic.chapter.subject  # 👈 Eng oxirgi ishlangan fan

            # 🔍 Shu fan bo‘yicha keyingi mavzuni topamiz
            chapter_topics = list(Topic.objects.filter(chapter=last_topic.chapter).order_by('order'))

            try:
                current_index = chapter_topics.index(last_topic)

                # Agar bu chapterdagi oxirgi mavzu bo‘lsa → keyingi chapterga o‘tamiz
                if current_index == len(chapter_topics) - 1:
                    next_chapter = Chapter.objects.filter(
                        subject=subject,
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
                return Response({
                    "topic_id": next_topic.id,
                    "subject_name_uz": subject.name_uz,
                    "subject_name_ru": subject.name_ru,
                    "chapter_name_uz": next_topic.chapter.name_uz,
                    "chapter_name_ru": next_topic.chapter.name_ru,
                    "topic_name_uz": next_topic.name_uz,
                    "topic_name_ru": next_topic.name_ru,
                    "score": 0,
                    "reminder_uz": f"{subject.name_uz} fanidan '{next_topic.name_uz}' mavzusini bajarish kerak!",
                    "reminder_ru": f"По предмету {subject.name_ru} необходимо выполнить тему «{next_topic.name_ru}»!"
                }, status=status.HTTP_200_OK)

        # 2️⃣ Agar hech qaysi mavzu ishlanmagan bo‘lsa — ro‘yxatdan o‘tgan fani bo‘yicha birinchi mavzuni ko‘rsatamiz
        if student.class_name:
            subject = student.class_name
            first_chapter = Chapter.objects.filter(subject=subject).order_by('order').first()
            if first_chapter:
                first_topic = Topic.objects.filter(chapter=first_chapter).order_by('order').first()
                if first_topic:
                    return Response({
                        "topic_id": first_topic.id,
                        "subject_name_uz": subject.name_uz,
                        "subject_name_ru": subject.name_ru,
                        "chapter_name_uz": first_chapter.name_uz,
                        "chapter_name_ru": first_chapter.name_ru,
                        "topic_name_uz": first_topic.name_uz,
                        "topic_name_ru": first_topic.name_ru,
                        "score": 0,
                        "reminder_uz": f"{subject.name_uz} fanidan '{first_topic.name_uz}' mavzusini boshlang!",
                        "reminder_ru": f"По предмету {subject.name_ru} начните тему «{first_topic.name_ru}»!"
                    }, status=status.HTTP_200_OK)

        # 3️⃣ Aks holda hech narsa yo‘q
        return Response({"detail": "Hozircha hech qanday mavzu mavjud emas."}, status=status.HTTP_204_NO_CONTENT)



class StudentLastProgressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # ✅ Faqat student kirishi mumkin
        if not hasattr(user, 'student_profile'):
            return Response(
                {"detail": "Faqat o‘quvchilar uchun."},
                status=status.HTTP_403_FORBIDDEN
            )

        student = user.student_profile

        # 🔍 Oxirgi ishlangan 5 ta mavzu
        progresses = (
            TopicProgress.objects
            .filter(user=student)
            .select_related(
                'topic',
                'topic__chapter',
                'topic__chapter__subject'
            )
            .order_by('-completed_at')[:5]
        )

        # 🆕 Agar hali hech narsa ishlanmagan bo‘lsa — bo‘sh list
        if not progresses.exists():
            return Response([], status=status.HTTP_200_OK)

        data = []

        for progress in progresses:
            topic = progress.topic
            chapter = topic.chapter
            subject = chapter.subject
            class_name =  chapter.subject.classes.name

            data.append({
                "class_name_uz": f"{class_name}-sinf",
                "class_name_ru": f"{class_name}-класс",
    
                "subject_name_uz": subject.name_uz,
                "subject_name_ru": subject.name_ru,
                "chapter_name_uz": chapter.name_uz,
                "chapter_name_ru": chapter.name_ru,
                "topic_name_uz": topic.name_uz,
                "topic_name_ru": topic.name_ru,
                "topic_id":topic.id,
                "score": round(progress.score, 1),
                "completed_at": (
                    progress.completed_at.strftime("%d/%m/%Y %H:%M")
                    if progress.completed_at else None
                )
            })

        return Response(data, status=status.HTTP_200_OK)
