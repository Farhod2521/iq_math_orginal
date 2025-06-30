from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.models import  TopicHelpRequestIndependent


class TeacherSubjectIndependentListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        teacher = request.user.teacher_profile
        help_requests = TopicHelpRequestIndependent.objects.filter(teacher=teacher)\
            .select_related('student__user', 'subject')\
            .prefetch_related('topics')

        response_data = []
        for req in help_requests:
            subject = req.subject
            class_name = getattr(subject, 'class_field', "1")
            topics = req.topics.all()

            response_data.append({
                "student_full_name": req.student.full_name,
                "class_uz": f"{class_name}-sinf {subject.name_uz}",
                "class_ru": f"{class_name}-класс {subject.name_ru}",
                "topics_name_uz": [topic.name_uz for topic in topics],
                "topics_name_ru": [topic.name_ru for topic in topics],
                "question_json": req.question_json,
                "result_json": req.result_json,
                "created_at": req.created_at,
            })

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