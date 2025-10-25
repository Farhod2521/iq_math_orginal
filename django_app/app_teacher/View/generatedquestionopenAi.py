from openai import OpenAI
import random
from django_app.app_teacher.models import Topic, Question, GeneratedQuestionOpenAi
import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import threading
from .generate_topic_questions_script import generate_topic_questions

class GenerateAIQuestionsAPIView(APIView):
    def post(self, request):
        topic_id = request.data.get("topic_id")
        threading.Thread(target=generate_topic_questions, args=(topic_id,)).start()
        return Response({"success": True, "message": "Jarayon boshlandi (AI generatsiya fon rejimida)."})
