from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_app.app_teacher.models import Topic
from django.shortcuts import get_object_or_404

class ReorderTopicAPIView(APIView):
    def post(self, request):
        """
        Drag & drop orqali kelgan `ordered_ids` asosida topiclarni tartiblaydi.
        Faqat bitta bob ichida ishlatiladi.
        """
        ordered_ids = request.data.get("ordered_ids", [])
        if not isinstance(ordered_ids, list):
            return Response({"detail": "ordered_ids list ko‘rinishida bo‘lishi kerak"}, status=400)

        for index, topic_id in enumerate(ordered_ids, start=1):  # 1 dan boshlaymiz
            try:
                Topic.objects.filter(id=topic_id).update(order=index)
            except Topic.DoesNotExist:
                continue

        return Response({"detail": "Tartib muvaffaqiyatli yangilandi"}, status=200)
