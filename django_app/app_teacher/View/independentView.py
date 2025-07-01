from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.models import  TopicHelpRequestIndependent
from rest_framework.pagination import PageNumberPagination

from collections import defaultdict

class TeacherTopicHelpRequestListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    # 👇 Ichki pagination class
    class StandardResultsSetPagination(PageNumberPagination):
        page_size = 10
        page_size_query_param = 'page_size'
        max_page_size = 100

    def get(self, request):
        help_requests = TopicHelpRequestIndependent.objects.all()\
            .select_related('student__user', 'subject')\
            .prefetch_related('topics')

        grouped_data = defaultdict(list)

        for req in help_requests:
            subject = req.subject
            class_name = getattr(subject, 'class_field', '1')  # default value
            topics = req.topics.all()
            status_text = "javob berilgan" if req.commit else "kutmoqda"

            grouped_data[req.student.id, req.student.full_name].append({
                "id": req.id,
                "class_uz": f"{class_name}-sinf {subject.name_uz}",
                "class_ru": f"{class_name}-класс {subject.name_ru}",
                "topics_name_uz": [topic.name_uz for topic in topics],
                "topics_name_ru": [topic.name_ru for topic in topics],
                "created_at": req.created_at,
                "status": status_text
            })

        response_data = [
            {
                "student_id": student_id,
                "student_full_name": full_name,
                "requests": reqs
            }
            for (student_id, full_name), reqs in grouped_data.items()
        ]

        # 👇 Paginationni qo‘llash
        paginator = self.StandardResultsSetPagination()
        paginated_page = paginator.paginate_queryset(response_data, request)
        return paginator.get_paginated_response(paginated_page)

from rest_framework.generics import RetrieveAPIView
class TeacherTopicHelpRequestDetailAPIView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    queryset = TopicHelpRequestIndependent.objects.all()
    lookup_field = 'id'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response({
            "question_json": instance.question_json,
            "result_json": instance.result_json
        })




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