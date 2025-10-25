from openai import OpenAI
import random
from django_app.app_teacher.models import Topic, Question, GeneratedQuestionOpenAi
import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .generate_topic_questions_script import generate_topic_questions

class GenerateAIQuestionsAPIView(APIView):
    def post(self, request):
        topic_id = request.data.get("topic_id")
        if not topic_id:
            return Response({"error": "topic_id kiritilishi kerak"}, status=400)

        try:
            count = generate_topic_questions(topic_id)
            return Response({"success": True, "generated_count": count}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

