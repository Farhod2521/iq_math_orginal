from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Max
from django_app.app_payments.models import Payment
from django_app.app_student.models import StudentScore,  Diagnost_Student, TopicProgress, StudentReferral
from django_app.app_user.models import Student, Subject
from django.shortcuts import get_object_or_404
from  django_app.app_student.serializers import  ReferredStudentSerializer

class StudentStatisticsDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        student = get_object_or_404(Student, id=student_id)
        score_data = StudentScore.objects.filter(student=student).first()
        all_payments = Payment.objects.filter(student=student)

        # Payment status counts
        success_payments = all_payments.filter(status='success')
        pending_payments = all_payments.filter(status='pending')
        failed_payments = all_payments.filter(status='failed')

        last_payment = success_payments.order_by('-payment_date').first()
        last_payment_date = last_payment.payment_date.strftime("%d/%m/%Y") if last_payment else None
        last_payment_time = last_payment.payment_date.strftime("%H:%M") if last_payment else None
        last_payment_amount = float(last_payment.amount) if last_payment else 0
        total_paid_amount = success_payments.aggregate(total=Sum('amount'))['total'] or 0

        # === Diagnostic data ===
        diagnostika = []
        student_diagnost_list = Diagnost_Student.objects.filter(student=student)

        for diagnost in student_diagnost_list:
            subject_name = diagnost.subject.name
            chapters_count = diagnost.chapters.count()
            topic_ids = diagnost.topic.values_list('id', flat=True)
            total_topics = len(topic_ids)

            # 80% dan yuqori bajarilganlar
            mastered_count = TopicProgress.objects.filter(
                user=student,
                topic_id__in=topic_ids,
                score__gte=80
            ).count()

            mastery_percent = round((mastered_count / total_topics) * 100, 1) if total_topics else 0

            diagnostika.append({
                "subject_name": subject_name,
                "chapters": chapters_count,
                "topics": total_topics,
                "mastered_topics": mastered_count,
                "mastery_percent": mastery_percent
            })

        # === Response JSON ===
        data = {
            'student_id': student.id,
            'full_name': student.full_name,
            'score': score_data.score if score_data else 0,
            'coin': score_data.coin if score_data else 0,
            'last_payment_date': last_payment_date,
            'last_payment_time': last_payment_time,
            'last_payment_amount': last_payment_amount,
            'payment_status_count': {
                'pending': pending_payments.count(),
                'success': success_payments.count(),
                'failed': failed_payments.count(),
            },
            'total_paid_amount': float(total_paid_amount),
            'student_diagnost': diagnostika
        }

        return Response(data)
    
class ChapterTopicProgressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id, subject_id):
        student = get_object_or_404(Student, id=student_id)
        subject = get_object_or_404(Subject, id=subject_id, active=True)

        result = []

        for chapter in subject.chapters.all().order_by('order'):
            chapter_data = {
                "chapter_id": chapter.id,
                "chapter_name": chapter.name,
                "topics": []
            }

            for topic in chapter.topics.all().order_by('order'):
                progress = TopicProgress.objects.filter(user=student, topic=topic).first()
                score = round(progress.score, 1) if progress else 0.0

                chapter_data["topics"].append({
                    "topic_id": topic.id,
                    "topic_name": topic.name,
                    "score_percent": score
                })

            result.append(chapter_data)

        return Response(result)

class SubjectListWithMasteryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        student = get_object_or_404(Student, id=student_id)
        result = []

        subjects = Subject.objects.filter(active=True).order_by('order')

        for subject in subjects:
            all_topic_count = 0
            mastered_topic_count = 0

            for chapter in subject.chapters.all():
                for topic in chapter.topics.all():
                    all_topic_count += 1
                    progress = TopicProgress.objects.filter(user=student, topic=topic).first()
                    if progress and progress.score >= 80:
                        mastered_topic_count += 1

            if all_topic_count == 0:
                continue

            mastery_percent = round((mastered_topic_count / all_topic_count) * 100, 1)

            # 🔒 Faqat mastery > 0 bo‘lsa, ro'yxatga qo‘shamiz
            if mastery_percent > 0:
                result.append({
                    "id": subject.id,
                    "name_uz": subject.name,  # Agar Translation ishlatilsa: subject.name_uz
                    "name_ru": subject.name,  # Agar Translation ishlatilsa: subject.name_ru
                    "class_name": subject.classes.name if subject.classes else "",
                    "class_uz": f"{subject.classes.name}-sinf {subject.name}" if subject.classes else subject.name,
                    "class_ru": f"{subject.classes.name}-класс {subject.name}" if subject.classes else subject.name,
                    "image_uz": subject.image_uz.url if subject.image_uz else None,
                    "image_ru": subject.image_ru.url if subject.image_ru else None,
                    "mastery_percent": mastery_percent
                })

        return Response(result)



########################################   DIAGNOSTIKA  ###############################################
class DiagnostSubjectListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        student = get_object_or_404(Student, id=student_id)

        # har bir subject uchun eng oxirgi diagnostika olish
        diagnost_entries = (
            Diagnost_Student.objects.filter(student=student)
            .select_related('subject')
            .prefetch_related('topic')
            .order_by('subject_id', '-created_at')
            .distinct('subject_id')  # PostgreSQLda ishlaydi
        )

        result = []

        for diagnost in diagnost_entries:
            subject = diagnost.subject
            topics = diagnost.topic.all()

            total = topics.count()
            mastered = 0

            for topic in topics:
                progress = TopicProgress.objects.filter(user=student, topic=topic).first()
                if progress and progress.score >= 80:
                    mastered += 1

            mastery_percent = round((mastered / total) * 100, 1) if total else 0.0

            result.append({
                "id": subject.id,
                "name_uz": subject.name,
                "name_ru": subject.name,
                "class_name": subject.classes.name if subject.classes else "",
                "class_uz": f"{subject.classes.name}-sinf {subject.name}" if subject.classes else subject.name,
                "class_ru": f"{subject.classes.name}-класс {subject.name}" if subject.classes else subject.name,
                "image_uz": subject.image_uz.url if subject.image_uz else None,
                "image_ru": subject.image_ru.url if subject.image_ru else None,
                "mastery_percent": mastery_percent
            })

        return Response(result)



class DiagnostChapterTopicProgressAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id, subject_id):
        student = get_object_or_404(Student, id=student_id)
        subject = get_object_or_404(Subject, id=subject_id, active=True)

        diagnost = Diagnost_Student.objects.filter(student=student, subject=subject).first()
        if not diagnost:
            return Response({"detail": "Diagnostika topilmadi"}, status=404)

        chapters = diagnost.chapters.all().order_by('order')
        topics_by_chapter = {
            chapter.id: [] for chapter in chapters
        }

        for topic in diagnost.topic.all():
            if topic.chapter_id in topics_by_chapter:
                topics_by_chapter[topic.chapter_id].append(topic)

        result = []
        for chapter in chapters:
            chapter_data = {
                "chapter_id": chapter.id,
                "chapter_name": chapter.name,
                "topics": []
            }

            topics = sorted(topics_by_chapter[chapter.id], key=lambda t: t.order)

            for topic in topics:
                progress = TopicProgress.objects.filter(user=student, topic=topic).first()
                score = round(progress.score, 1) if progress else 0.0

                chapter_data["topics"].append({
                    "topic_id": topic.id,
                    "topic_name": topic.name,
                    "score_percent": score
                })

            result.append(chapter_data)

        return Response(result)
    



class MyReferralsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = request.user.student_profile  # Agar sizda `user -> student` bog‘lanishi bo‘lsa
        referrals = StudentReferral.objects.filter(referrer=student)
        serializer = ReferredStudentSerializer(referrals, many=True)
        return Response(serializer.data)