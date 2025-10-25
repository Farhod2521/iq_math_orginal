from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .generate_topic_questions_script import generate_topic_questions

class GenerateAIQuestionsAPIView(APIView):
    def post(self, request):
        subject_id = request.data.get("subject_id")
        chapter_id = request.data.get("chapter_id")
        topic_id = request.data.get("topic_id")

        if not (subject_id and chapter_id and topic_id):
            return Response({"error": "subject_id, chapter_id va topic_id kiritilishi kerak"}, status=400)

        try:
            count = generate_topic_questions(subject_id, chapter_id, topic_id)
            return Response({"success": True, "generated_count": count}, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
