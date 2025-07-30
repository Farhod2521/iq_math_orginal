from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.models import  TopicHelpRequestIndependent
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from collections import defaultdict
from django.utils import timezone  


class TeacherTopicHelpRequestListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    class StandardResultsSetPagination(PageNumberPagination):
        page_size = 10
        page_size_query_param = 'page_size'
        max_page_size = 100

    def get(self, request):
        help_requests = TopicHelpRequestIndependent.objects.all()\
            .select_related('student__user', 'subject', 'teacher__user')\
            .prefetch_related('topics')

        grouped_data = defaultdict(list)

        for req in help_requests:
            subject = req.subject
            class_name = getattr(subject, 'class_field', '1')  # default value
            topics = req.topics.all()
            status_text = "javob berilgan" if req.commit else "kutmoqda"

            teacher_info = None
            if req.teacher:
                teacher_info = {
                    "full_name": req.teacher.full_name,
                    "reviewed_at": req.reviewed_at,
                    "commit": req.commit
                }

            grouped_data[req.student.id, req.student.full_name].append({
                "id": req.id,
                "class_uz": f"{class_name}-sinf {subject.name_uz}",
                "class_ru": f"{class_name}-класс {subject.name_ru}",
                "topics_name_uz": [topic.name_uz for topic in topics],
                "topics_name_ru": [topic.name_ru for topic in topics],
                "created_at": req.created_at,
                "status": status_text,
                "teacher": teacher_info  # 👈 qo‘shilgan qism
            })

        response_data = [
            {
                "student_id": student_id,
                "student_full_name": full_name,
                "requests": reqs
            }
            for (student_id, full_name), reqs in grouped_data.items()
        ]

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





class TeacherCommitToHelpRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            teacher = request.user.teacher_profile
        except AttributeError:
            return Response({"error": "Siz o‘qituvchi emassiz"}, status=status.HTTP_403_FORBIDDEN)

        help_request_id = request.data.get("help_request_id")
        commit = request.data.get("commit")

        if not help_request_id or not commit:
            return Response(
                {"error": "help_request_id va commit maydonlari majburiy"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            help_request = TopicHelpRequestIndependent.objects.get(id=help_request_id)
        except TopicHelpRequestIndependent.DoesNotExist:
            return Response(
                {"error": "Ushbu so‘rov mavjud emas"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Commit va o‘qituvchini yozamiz
        help_request.teacher = teacher
        help_request.commit = commit
        help_request.reviewed_at = timezone.now()
        help_request.save()

        return Response({"success": "Izoh muvaffaqiyatli yozildi"}, status=status.HTTP_200_OK)


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