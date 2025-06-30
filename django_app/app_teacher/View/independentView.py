from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.models import  TopicHelpRequestIndependent


from collections import defaultdict

class TeacherSubjectIndependentListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        help_requests = TopicHelpRequestIndependent.objects.all()\
            .select_related('student__user', 'subject')\
            .prefetch_related('topics')

        # 🧠 Student bo‘yicha guruhlab boramiz
        grouped_data = defaultdict(list)

        for req in help_requests:
            subject = req.subject
            class_name = getattr(subject, 'class_field', "1")
            topics = req.topics.all()

            status_text = "javob berilgan" if req.commit else "kutmoqda"

            grouped_data[req.student.full_name].append({
                "class_uz": f"{class_name}-sinf {subject.name_uz}",
                "class_ru": f"{class_name}-класс {subject.name_ru}",
                "topics_name_uz": [topic.name_uz for topic in topics],
                "topics_name_ru": [topic.name_ru for topic in topics],
                "question_json": req.question_json,
                "result_json": req.result_json,
                "created_at": req.created_at,
                "status": status_text
            })

        # 🔁 Yakuniy formatga keltiramiz
        response_data = [
            {
                "student_full_name": full_name,
                "requests": requests
            }
            for full_name, requests in grouped_data.items()
        ]

        return Response(response_data)




# class TeacherTopicHelpRequestBySubjectView(ListAPIView):
#     serializer_class = TopicHelpRequestIndependentSerializer
#     permission_classes = [IsAuthenticated]

#     def get_queryset(self):
#         user = self.request.user
#         subject_id = self.kwargs.get('subject_id')
#         return TopicHelpRequestIndependent.objects.filter(
#             teacher=user.teacher_profile,
#             subject_id=subject_id
#         )