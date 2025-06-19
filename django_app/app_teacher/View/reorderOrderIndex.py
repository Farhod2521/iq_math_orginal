from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_app.app_teacher.models import Topic, Chapter
from django.shortcuts import get_object_or_404

class ReorderTopicAPIView(APIView):
    def post(self, request):
        # ✅ Faqat teacher foydalanuvchilarga ruxsat beramiz
        if not hasattr(request.user, 'teacher_profile'):
            return Response({"detail": "Faqat o‘qituvchilar uchun ruxsat berilgan."}, status=403)

        ordered_ids = request.data.get("ordered_ids", [])
        if not isinstance(ordered_ids, list):
            return Response({"detail": "ordered_ids list ko‘rinishida bo‘lishi kerak"}, status=400)

        for index, topic_id in enumerate(ordered_ids, start=1):
            Topic.objects.filter(id=topic_id).update(order=index)

        return Response({"detail": "Tartib muvaffaqiyatli yangilandi"}, status=200)

class ReorderChapterAPIView(APIView):
    def post(self, request):
        # ✅ Faqat teacher foydalanuvchilarga ruxsat beramiz
        if not hasattr(request.user, 'teacher_profile'):
            return Response({"detail": "Faqat o‘qituvchilar uchun ruxsat berilgan."}, status=403)

        ordered_ids = request.data.get("ordered_ids", [])
        if not isinstance(ordered_ids, list):
            return Response({"detail": "ordered_ids list bo‘lishi kerak"}, status=400)

        for index, chapter_id in enumerate(ordered_ids, start=1):
            Chapter.objects.filter(id=chapter_id).update(order=index)

        return Response({"detail": "Chapter tartibi muvaffaqiyatli yangilandi"}, status=200)