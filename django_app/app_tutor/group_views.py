"""
O'qituvchi (tutor) guruhlari: yaratish, ro'yxat, tahrirlash, o'chirish va
guruhga o'quvchi qo'shish / olib tashlash.

Tutor faqat o'zining promo havolasi yoki kuponi orqali qo'shilgan o'quvchilarini
guruhlarga ajrata oladi.
"""

from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_user.models import Student

from .helpers import IsTutor, get_tutor, get_tutor_students
from .models import TutorGroup
from .serializers import (
    TutorGroupDetailSerializer,
    TutorGroupListSerializer,
    TutorGroupWriteSerializer,
    TutorStudentBriefSerializer,
)


def _students_with_groups(queryset, tutor):
    """group_id/group_name ni ortiqcha so'rovsiz olish uchun tutor guruhlarini prefetch qilamiz."""
    return queryset.prefetch_related(
        Prefetch('tutor_groups', queryset=TutorGroup.objects.filter(tutor=tutor))
    )


def _tutor_groups(tutor):
    """Guruh queryset'i — o'quvchilari va ularning guruh nomlari bilan birga."""
    students_qs = _students_with_groups(
        Student.objects.select_related('user', 'class_name', 'class_name__classes'),
        tutor
    )
    return TutorGroup.objects.filter(tutor=tutor).prefetch_related(
        Prefetch('students', queryset=students_qs)
    )


class TutorGroupListCreateAPIView(APIView):
    """
    GET  /api/v1/tutor/tutor/groups/ - tutor guruhlari ro'yxati
    POST /api/v1/tutor/tutor/groups/ - guruh yaratish {name, description?, student_ids?}
    """
    permission_classes = [IsTutor]

    def get(self, request):
        tutor = get_tutor(request)
        groups = _tutor_groups(tutor)

        search = request.GET.get('search')
        if search:
            groups = groups.filter(name__icontains=search)

        is_active = request.GET.get('is_active')
        if is_active is not None:
            groups = groups.filter(is_active=is_active.lower() in ('1', 'true', 'yes'))

        serializer = TutorGroupListSerializer(groups, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        tutor = get_tutor(request)
        serializer = TutorGroupWriteSerializer(data=request.data, context={'tutor': tutor})
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        return Response(
            TutorGroupDetailSerializer(group, context={'tutor': tutor}).data,
            status=status.HTTP_201_CREATED
        )


class TutorGroupDetailAPIView(APIView):
    """
    GET    /api/v1/tutor/tutor/groups/<pk>/ - guruh detali (o'quvchilari bilan)
    PUT    /api/v1/tutor/tutor/groups/<pk>/ - to'liq tahrirlash
    PATCH  /api/v1/tutor/tutor/groups/<pk>/ - qisman tahrirlash
    DELETE /api/v1/tutor/tutor/groups/<pk>/ - o'chirish
    """
    permission_classes = [IsTutor]

    def _get_group(self, request, pk):
        return get_object_or_404(_tutor_groups(get_tutor(request)), pk=pk)

    def get(self, request, pk):
        tutor = get_tutor(request)
        group = self._get_group(request, pk)
        serializer = TutorGroupDetailSerializer(group, context={'tutor': tutor})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        tutor = get_tutor(request)
        group = self._get_group(request, pk)
        serializer = TutorGroupWriteSerializer(
            group, data=request.data, partial=partial, context={'tutor': tutor}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            TutorGroupDetailSerializer(self._get_group(request, pk), context={'tutor': tutor}).data,
            status=status.HTTP_200_OK
        )

    def delete(self, request, pk):
        group = self._get_group(request, pk)
        group.delete()
        return Response({"message": "Guruh o'chirildi"}, status=status.HTTP_200_OK)


class TutorGroupStudentsAPIView(APIView):
    """
    POST   /api/v1/tutor/tutor/groups/<pk>/students/ - {student_ids: []} guruhga qo'shish
    DELETE /api/v1/tutor/tutor/groups/<pk>/students/ - {student_ids: []} guruhdan chiqarish
    """
    permission_classes = [IsTutor]

    def _get_group(self, request, pk):
        return get_object_or_404(_tutor_groups(get_tutor(request)), pk=pk)

    def _student_ids(self, request):
        student_ids = request.data.get('student_ids')
        if student_ids is None:
            student_id = request.data.get('student_id')
            student_ids = [student_id] if student_id else []
        if not isinstance(student_ids, list):
            student_ids = [student_ids]
        return [sid for sid in student_ids if sid]

    def post(self, request, pk):
        tutor = get_tutor(request)
        group = self._get_group(request, pk)
        student_ids = self._student_ids(request)

        if not student_ids:
            return Response({"error": "student_ids bo'sh"}, status=status.HTTP_400_BAD_REQUEST)

        allowed_students = get_tutor_students(tutor).filter(id__in=student_ids)
        allowed_ids = set(allowed_students.values_list('id', flat=True))
        invalid_ids = [sid for sid in student_ids if sid not in allowed_ids]
        if invalid_ids:
            return Response(
                {"error": f"Bu o'quvchilar sizning o'quvchilaringiz emas: {invalid_ids}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Bir o'quvchi bir vaqtda tutorning faqat bitta guruhida bo'ladi
        for other_group in TutorGroup.objects.filter(tutor=tutor).exclude(pk=group.pk):
            other_group.students.remove(*allowed_students)
        group.students.add(*allowed_students)

        return Response(
            TutorGroupDetailSerializer(self._get_group(request, pk), context={'tutor': tutor}).data,
            status=status.HTTP_200_OK
        )

    def delete(self, request, pk):
        tutor = get_tutor(request)
        group = self._get_group(request, pk)
        student_ids = self._student_ids(request)

        if not student_ids:
            return Response({"error": "student_ids bo'sh"}, status=status.HTTP_400_BAD_REQUEST)

        students = Student.objects.filter(id__in=student_ids)
        group.students.remove(*students)

        return Response(
            TutorGroupDetailSerializer(self._get_group(request, pk), context={'tutor': tutor}).data,
            status=status.HTTP_200_OK
        )


class TutorStudentListAPIView(APIView):
    """
    GET /api/v1/tutor/tutor/my-students/ - tutor promo/kupon orqali qo'shgan o'quvchilar.

    Query params:
      ?search=<ism, ID yoki telefon>
      ?group_id=<id>        - shu guruhdagilar
      ?without_group=true   - hech qaysi guruhga kiritilmaganlar
    """
    permission_classes = [IsTutor]

    def get(self, request):
        tutor = get_tutor(request)
        students = get_tutor_students(tutor)

        search = request.GET.get('search')
        if search:
            students = students.filter(
                Q(full_name__icontains=search)
                | Q(identification__icontains=search)
                | Q(user__phone__icontains=search)
            )

        group_id = request.GET.get('group_id')
        if group_id:
            students = students.filter(tutor_groups__id=group_id, tutor_groups__tutor=tutor)

        without_group = request.GET.get('without_group')
        if without_group and without_group.lower() in ('1', 'true', 'yes'):
            grouped_ids = TutorGroup.objects.filter(tutor=tutor).values_list('students__id', flat=True)
            students = students.exclude(id__in=[sid for sid in grouped_ids if sid])

        students = _students_with_groups(students.distinct(), tutor)
        serializer = TutorStudentBriefSerializer(students, many=True, context={'tutor': tutor})
        return Response(serializer.data, status=status.HTTP_200_OK)
