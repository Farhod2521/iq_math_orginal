from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from django_app.app_user.models import Student, Subject
from django_app.app_student.models import Diagnost_Student
from django_app.app_teacher.models import Chapter




class StudentDiagnostSubjectsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = Student.objects.get(user=request.user)

        diagnost_list = Diagnost_Student.objects.filter(student=student).select_related('subject').distinct('subject')

        data = []
        for d in diagnost_list:
            subject = d.subject
            if subject:
                class_name = subject.classes.name if subject.classes else ""
                data.append({
                    "id": subject.id,
                    "name_uz": subject.name_uz,
                    "name_ru": subject.name_ru,
                    "class_name": class_name,
                    "class_uz": f"{class_name}-sinf {subject.name_uz}",
                    "class_ru": f"{class_name}-класс {subject.name_ru}",
                    "image_uz": subject.image_uz.url if subject.image_uz else "",
                    "image_ru": subject.image_ru.url if subject.image_ru else "",
                    "is_open": True  # yoki kerakli shart bilan o‘zgartirsa ham bo‘ladi
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