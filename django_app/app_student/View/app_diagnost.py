from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from django_app.app_user.models import Student, Subject
from django_app.app_student.models import Diagnost_Student, TopicProgress
from django_app.app_teacher.models import Chapter, Topic

from rest_framework import status

class StudentDiagnostSubjectsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = Student.objects.get(user=request.user)

        diagnost_dict = {}
        diagnost_list = Diagnost_Student.objects.filter(student=student).select_related('subject')

        for d in diagnost_list:
            # Har bir subject bo‘yicha oxirgi diagnostika yozuvini olish
            latest_diagnost = Diagnost_Student.objects.filter(
                student=student,
                subject=d.subject
            ).order_by('-id').first()

            progress_percent = None
            if latest_diagnost and latest_diagnost.result:
                try:
                    # result JSON ichidan score olish
                    score = latest_diagnost.result.get("result", [{}])[0].get("score")
                    if score is not None:
                        progress_percent = score
                except Exception:
                    progress_percent = None

            diagnost_dict[d.subject.id] = progress_percent

        # Barcha fanlarni olamiz
        subjects = Subject.objects.all().select_related('classes')
        data = []
        for subject in subjects:
            class_name = subject.classes.name if subject.classes else ""
            progress_percent = diagnost_dict.get(subject.id)

            has_diagnost = Diagnost_Student.objects.filter(student=student, subject=subject).exists()

            data.append({
                "id": subject.id,
                "name_uz": subject.name_uz,
                "name_ru": subject.name_ru,
                "class_name": class_name,
                "class_uz": f"{class_name}-sinf {subject.name_uz}",
                "class_ru": f"{class_name}-класс {subject.name_ru}",
                "image_uz": subject.image_uz.url if subject.image_uz else "",
                "image_ru": subject.image_ru.url if subject.image_ru else "",
                "progress_percent": progress_percent,   # ✅ endi oxirgi score chiqadi
                "has_taken_diagnostic": has_diagnost
            })

        return Response(data)

class SubjectChaptersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, subject_id):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({"message": "Foydalanuvchi topilmadi"}, status=404)

        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({"message": "Fan topilmadi"}, status=404)

        # Eng so‘nggi diagnostika (agar ko‘pi bo‘lsa)
        diagnost = Diagnost_Student.objects.filter(student=student, subject=subject).order_by('-id').first()
        if not diagnost:
            return Response({"message": "Ushbu fan bo‘yicha diagnostika topilmadi"}, status=404)

        # ✅ Faqat xato bo‘lgan boblar
        chapters = diagnost.chapters.all()
        data = [
            {"id": ch.id, "name_uz": ch.name_uz, "name_ru": ch.name_ru}
            for ch in chapters
        ]
        return Response(data)
class ChapterTopicsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, chapter_id):
        try:
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response({"message": "Foydalanuvchi topilmadi"}, status=404)

        try:
            chapter = Chapter.objects.get(id=chapter_id)
        except Chapter.DoesNotExist:
            return Response({"message": "Bob topilmadi"}, status=404)

        # Ushbu bob qaysi fanga tegishli
        subject = chapter.subject

        # Eng so‘nggi diagnostikani topamiz
        diagnost = Diagnost_Student.objects.filter(student=student, subject=subject).order_by('-id').first()
        if not diagnost:
            return Response({"message": "Diagnostika topilmadi"}, status=404)

        # ✅ Faqat shu bobga tegishli va noto‘g‘ri ishlangan topiclar
        topics = diagnost.topic.filter(chapter=chapter)

        data = [
            {"id": topic.id, "name_uz": topic.name_uz, "name_ru": topic.name_ru}
            for topic in topics
        ]
        return Response(data)
    


class ParentStudentDiagnosticHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 🔒 Faqat parent
        if user.role != "parent":
            return Response(
                {"detail": "Faqat ota-ona uchun ruxsat berilgan"},
                status=status.HTTP_403_FORBIDDEN
            )

        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response(
                {"detail": "student_id majburiy"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response(
                {"detail": "Student topilmadi"},
                status=status.HTTP_404_NOT_FOUND
            )

        diagnost_dict = {}

        diagnost_list = (
            Diagnost_Student.objects
            .filter(student=student)
            .select_related("subject")
            .prefetch_related("topic")
        )

        for d in diagnost_list:
            subject = d.subject
            subject_id = subject.id

            all_diagnosts = (
                Diagnost_Student.objects
                .filter(student=student, subject=subject)
                .prefetch_related("topic")
                .order_by("id")
            )

            progress_history = []
            topic_counter = {}

            for diag in all_diagnosts:
                # 📊 Ball tarixi
                if diag.result:
                    try:
                        score = diag.result.get("result", [{}])[0].get("score")
                        if score is not None:
                            progress_history.append({
                                "date": diag.create_date.strftime("%Y-%m-%d %H:%M") if diag.create_date else None,
                                "score": score
                            })
                    except Exception:
                        pass

                # 🔁 Takrorlangan mavzular
                for topic in diag.topic.all():
                    topic_counter[topic.id] = topic_counter.get(topic.id, 0) + 1

            repeated_topics = [
                {
                    "id": t.id,
                    "name_uz": t.name_uz,
                    "name_ru": t.name_ru,
                    "repeat_count": topic_counter[t.id]
                }
                for t in Topic.objects.filter(
                    id__in=[tid for tid, count in topic_counter.items() if count >= 3]
                )
            ]

            progress_percent = progress_history[-1]["score"] if progress_history else None
            last_date = progress_history[-1]["date"] if progress_history else None

            diagnost_dict[subject_id] = {
                "progress_history": progress_history,
                "progress_percent": progress_percent,
                "last_date": last_date,
                "repeated_topics": repeated_topics
            }

        subjects = (
            Subject.objects
            .filter(id__in=diagnost_dict.keys())
            .select_related("classes")
        )

        data = []
        for subject in subjects:
            class_name = subject.classes.name if subject.classes else ""
            info = diagnost_dict[subject.id]

            data.append({
                "id": subject.id,
                "name_uz": subject.name_uz,
                "name_ru": subject.name_ru,
                "class_name": class_name,
                "class_uz": f"{class_name}-sinf {subject.name_uz}",
                "class_ru": f"{class_name}-класс {subject.name_ru}",
                "image_uz": subject.image_uz.url if subject.image_uz else "",
                "image_ru": subject.image_ru.url if subject.image_ru else "",
                "progress_percent": info["progress_percent"],
                "progress_history": info["progress_history"],
                "last_date": info["last_date"],
                "has_taken_diagnostic": True,
                "repeated_topics": info["repeated_topics"]
            })

        return Response(data, status=status.HTTP_200_OK)



class StudentDiagnosticHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = Student.objects.get(user=request.user)
        diagnost_dict = {}
        diagnost_list = Diagnost_Student.objects.filter(student=student).select_related('subject')

        for d in diagnost_list:
            subject = d.subject
            subject_id = subject.id

            # Shu fanga tegishli barcha diagnostikalar
            all_diagnosts = Diagnost_Student.objects.filter(
                student=student,
                subject=subject
            ).prefetch_related('topic').order_by('id')

            progress_history = []
            topic_counter = {}

            for diag in all_diagnosts:
                # 🔹 Ball tarixini yig‘ish
                if diag.result:
                    try:
                        score = diag.result.get("result", [{}])[0].get("score")
                        if score is not None:
                            progress_history.append({
                                "date": diag.create_date.strftime("%Y-%m-%d %H:%M") if diag.create_date else None,
                                "score": score
                            })
                    except Exception:
                        continue

                # 🔹 Mavzularni hisoblash
                for topic in diag.topic.all():
                    topic_counter[topic.id] = topic_counter.get(topic.id, 0) + 1

            # 🔹 3 martadan ko‘p takrorlangan mavzular
            repeated_topics = [
                {
                    "id": t.id,
                    "name_uz": t.name_uz,
                    "name_ru": t.name_ru,
                    "repeat_count": topic_counter[t.id]
                }
                for t in Topic.objects.filter(id__in=[
                    tid for tid, count in topic_counter.items() if count >= 3
                ])
            ]

            # Oxirgi ball va sana
            progress_percent = progress_history[-1]["score"] if progress_history else None
            last_date = progress_history[-1]["date"] if progress_history else None

            diagnost_dict[subject_id] = {
                "progress_history": progress_history,
                "progress_percent": progress_percent,
                "last_date": last_date,
                "repeated_topics": repeated_topics
            }

        # Faqat diagnostika o‘tkazilgan fanlar
        subjects = Subject.objects.filter(id__in=diagnost_dict.keys()).select_related('classes')

        data = []
        for subject in subjects:
            class_name = subject.classes.name if subject.classes else ""
            diagnost_info = diagnost_dict[subject.id]

            data.append({
                "id": subject.id,
                "name_uz": subject.name_uz,
                "name_ru": subject.name_ru,
                "class_name": class_name,
                "class_uz": f"{class_name}-sinf {subject.name_uz}",
                "class_ru": f"{class_name}-класс {subject.name_ru}",
                "image_uz": subject.image_uz.url if subject.image_uz else "",
                "image_ru": subject.image_ru.url if subject.image_ru else "",
                "progress_percent": diagnost_info["progress_percent"],
                "progress_history": diagnost_info["progress_history"],
                "last_date": diagnost_info["last_date"],
                "has_taken_diagnostic": True,
                # 🆕 Takrorlangan mavzularni massiv shaklida qaytarish
                "repeated_topics": diagnost_info["repeated_topics"]
            })

        return Response(data)
