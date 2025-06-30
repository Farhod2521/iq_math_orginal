from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.models import  TopicHelpRequestIndependent


class TeacherSubjectIndependentListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        teacher = request.user.teacher_profile
        help_requests = TopicHelpRequestIndependent.objects.filter(teacher=teacher).select_related('subject')
        unique_subjects = {}

        for req in help_requests:
            subj = req.subject
            if subj.id not in unique_subjects:
                class_name = subj.class_field if hasattr(subj, 'class_field') else "1"
                unique_subjects[subj.id] = {
                    "id": subj.id,
                    "name_uz": subj.name_uz,
                    "name_ru": subj.name_ru,
                    "class_name": class_name,
                    "class_uz": f"{class_name}-sinf {subj.name_uz}",
                    "class_ru": f"{class_name}-класс {subj.name_ru}",
                    "image_uz": subj.image_uz.url if subj.image_uz else "",
                    "image_ru": subj.image_ru.url if subj.image_ru else ""
                }

        return Response(list(unique_subjects.values()))


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