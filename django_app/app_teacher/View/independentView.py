from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_app.app_student.models import  TopicHelpRequestIndependent
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from collections import defaultdict
from django.utils import timezone  
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from django_app.app_user.models import  Teacher, User


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
            class_name = subject.classes.name if subject.classes else 'Nomalum'
            topics = req.topics.all()
            status_text = "javob berilgan" if req.commit else "kutmoqda"

            teacher_info = None
            if req.teacher:
                teacher_info = {
                    "full_name": req.teacher.full_name,
                    "reviewed_at": req.reviewed_at,
                    "commit": req.commit
                }

            created_at_formatted = req.created_at.strftime("%d.%m.%Y %H:%M") if req.created_at else None

            grouped_data[req.student.id, req.student.full_name].append({
                "id": req.id,
                "class_uz": f"{class_name}-sinf {subject.name_uz}",
                "class_ru": f"{class_name}-класс {subject.name_ru}",
                "topics_name_uz": [topic.name_uz for topic in topics],
                "topics_name_ru": [topic.name_ru for topic in topics],
                "created_at": created_at_formatted,
                "status": status_text,
                "teacher": teacher_info
            })

        # 🔽 Har bir student uchun sahifalangan requestlar
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size

        response_data = [
            {
                "student_id": student_id,
                "student_full_name": full_name,
                "requests": reqs[start:end],  # sahifalab kesiladi
                "total_requests": len(reqs),  # umumiy sonni ham ko‘rsatamiz
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


class TeacherTopicHelpRequestFromTelegramAPIView(APIView):
    permission_classes = [AllowAny]

    class StandardResultsSetPagination(PageNumberPagination):
        page_size = 10
        page_size_query_param = 'page_size'
        max_page_size = 100

    def post(self, request):
        telegram_id = request.data.get('telegram_id')

        if not telegram_id:
            return Response({'error': 'telegram_id majburiy'}, status=400)

        user = get_object_or_404(User, telegram_id=telegram_id, role='teacher')

        # Faqat status='sent' bo'lgan va hali o‘qituvchi biriktirilmagan (kutmoqda holati)
        help_requests = TopicHelpRequestIndependent.objects.filter(
            status='sent',
            teacher__isnull=True
        ).select_related('student__user', 'subject')\
         .prefetch_related('topics')

        grouped_data = defaultdict(list)

        for req in help_requests:
            subject = req.subject
            class_name = getattr(subject, 'class_field', '1')
            topics = req.topics.all()
            status_text = "kutmoqda" if not req.commit else "javob berilgan"

            teacher_info = None
            if req.teacher:
                teacher_info = {
                    "full_name": req.teacher.full_name,
                    "reviewed_at": req.reviewed_at,
                    "commit": req.commit
                }

            grouped_data[(req.student.id, req.student.full_name)].append({
                "id": req.id,
                "class_uz": f"{class_name}-sinf {subject.name_uz}",
                "class_ru": f"{class_name}-класс {subject.name_ru}",
                "topics_name_uz": [topic.name_uz for topic in topics],
                "topics_name_ru": [topic.name_ru for topic in topics],
                "created_at": req.created_at,
                "status": status_text,
                "teacher": teacher_info
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
    

class GetTelegramIDFromHelpRequestAPIView(APIView):


    def get(self, request, pk):
        try:
            help_request = TopicHelpRequestIndependent.objects.select_related('student__user').get(pk=pk)
        except TopicHelpRequestIndependent.DoesNotExist:
            return Response({'detail': 'Bunday IDga ega so‘rov topilmadi.'}, status=status.HTTP_404_NOT_FOUND)
        
        telegram_id = help_request.student.user.telegram_id
        return Response({'telegram_id': telegram_id})



class TeacherHelpRequestNotificationAPIView(APIView):
    """
    Qo‘ng‘iroqcha uchun xabarlar soni, statistikasi va ularni 'Ko‘rildi' deb belgilash
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        teacher = getattr(request.user, 'teacher_profile', None)
        if not teacher:
            return Response(
                {"detail": "Foydalanuvchi o‘qituvchi emas."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 🔹 Statistik ma'lumotlar
        base_qs = TopicHelpRequestIndependent.objects.filter(teacher=teacher)
        total_count = base_qs.count()
        unread_count = base_qs.filter(status='sent', is_seen=False).count()

        stats = {
            "sent": base_qs.filter(status='sent').count(),
            "seen": base_qs.filter(status='seen').count(),
            "reviewing": base_qs.filter(status='reviewing').count(),
            "answered": base_qs.filter(status='answered').count(),
            "closed": base_qs.filter(status='closed').count(),
            "rejected": base_qs.filter(status='rejected').count(),
        }

        # 🔹 Oxirgi 10 ta yuborilgan murojaat (eng yangilari birinchi)
        latest_requests = base_qs.order_by('-created_at')[:10]
        latest_list = [
            {
                "id": item.id,
                "student": item.student.full_name if item.student else None,
                "subject": item.subject.name_uz if item.subject else None,
                "status": item.status,
                "created_at": item.created_at.strftime("%d/%m/%Y %H:%M"),
                "is_seen": item.is_seen,
            }
            for item in latest_requests
        ]

        return Response({
            "total_requests": total_count,
            "unread_count": unread_count,
            "status_breakdown": stats,
            "latest_requests": latest_list,
        }, status=status.HTTP_200_OK)

    def post(self, request):
        teacher = getattr(request.user, 'teacher_profile', None)
        if not teacher:
            return Response(
                {"detail": "Foydalanuvchi o‘qituvchi emas."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 🔹 faqat 10 ta "sent" yozuvni yangilaymiz
        to_update = TopicHelpRequestIndependent.objects.filter(
            teacher=teacher,
            status='sent',
            is_seen=False
        )[:10]

        updated_count = to_update.count()
        now = timezone.now()

        for record in to_update:
            record.is_seen = True
            record.status = 'seen'
            record.reviewed_at = now
            record.save(update_fields=['is_seen', 'status', 'reviewed_at'])

        return Response({
            "marked_as_seen": updated_count,
            "message": f"{updated_count} ta murojaat 'Ko‘rildi' holatiga o‘tkazildi."
        })