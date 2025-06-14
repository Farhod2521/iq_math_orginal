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
        data = [
            {
                "id": d.subject.id,
                "name_uz": d.subject.name_uz,
                "name_ru": d.subject.name_ru,
                "class_uz": f"{d.subject.classes.name}-sinf {d.subject.name_uz}",
                "class_ru": f"{d.subject.classes.name}-класс {d.subject.name_ru}"
            }
            for d in diagnost_list if d.subject
        ]
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