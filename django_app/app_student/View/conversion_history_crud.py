from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404

from django_app.app_student.models import ConversionHistory
from django_app.app_user.models import Student


class IsSuperAdminOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and getattr(request.user, 'role', None) in ('superadmin', 'admin')
        )


class ConversionHistoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200


def _serialize_conversion(obj):
    student = obj.student
    return {
        "id": obj.id,
        "student": {
            "id": student.id,
            "full_name": student.full_name,
            "phone": student.user.phone,
        },
        "conversion_type": obj.conversion_type,
        "conversion_type_display": obj.get_conversion_type_display(),
        "amount_from": obj.amount_from,
        "amount_to": obj.amount_to,
        "som_after": obj.som_after,
        "comment": obj.comment,
        "status": obj.status,
        "status_display": obj.get_status_display(),
        "created_at": obj.created_at.strftime("%d/%m/%Y %H:%M"),
    }


def _build_qs():
    return ConversionHistory.objects.select_related(
        'student__user'
    ).order_by('-created_at')


# ════════════════════════════════════════════════════════════════════
#  SUPERADMIN — ConversionHistory CRUD
#  GET    /api/v1/student/conversion-history/           → ro'yxat
#  GET    /api/v1/student/conversion-history/<pk>/      → bitta
#  POST   /api/v1/student/conversion-history/           → yaratish
#  PUT    /api/v1/student/conversion-history/<pk>/      → yangilash
#  DELETE /api/v1/student/conversion-history/<pk>/      → o'chirish
# ════════════════════════════════════════════════════════════════════
class ConversionHistoryCRUDAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    # ── LIST / DETAIL ─────────────────────────────────────────────
    def get(self, request, pk=None):
        if pk:
            obj = get_object_or_404(_build_qs(), pk=pk)
            return Response(_serialize_conversion(obj))

        qs = _build_qs()

        # Filter: ?student_id=5
        student_id = request.query_params.get('student_id')
        if student_id:
            qs = qs.filter(student_id=student_id)

        # Filter: ?conversion_type=SCORE_TO_COIN
        conversion_type = request.query_params.get('conversion_type')
        valid_types = ('SCORE_TO_COIN', 'SCORE_TO_SOM', 'COIN_TO_SOM')
        if conversion_type in valid_types:
            qs = qs.filter(conversion_type=conversion_type)

        # Filter: ?status=pending
        status_param = request.query_params.get('status')
        valid_statuses = ('pending', 'approved', 'rejected')
        if status_param in valid_statuses:
            qs = qs.filter(status=status_param)

        paginator = ConversionHistoryPagination()
        page = paginator.paginate_queryset(qs, request)
        data = [_serialize_conversion(obj) for obj in page]
        return paginator.get_paginated_response(data)

    # ── CREATE ────────────────────────────────────────────────────
    def post(self, request):
        data = request.data

        student_id = data.get('student_id')
        if not student_id:
            return Response(
                {"message": "student_id maydoni talab qilinadi"},
                status=status.HTTP_400_BAD_REQUEST
            )

        student = get_object_or_404(Student, pk=student_id)

        conversion_type = data.get('conversion_type')
        valid_types = ('SCORE_TO_COIN', 'SCORE_TO_SOM', 'COIN_TO_SOM')
        if conversion_type not in valid_types:
            return Response(
                {"message": f"conversion_type noto'g'ri. To'g'ri qiymatlar: {valid_types}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        amount_from = data.get('amount_from')
        amount_to = data.get('amount_to')
        if amount_from is None or amount_to is None:
            return Response(
                {"message": "amount_from va amount_to maydonlari talab qilinadi"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount_from = int(amount_from)
            amount_to = int(amount_to)
        except (ValueError, TypeError):
            return Response(
                {"message": "amount_from va amount_to butun son bo'lishi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )

        conv_status = data.get('status', 'approved')
        valid_statuses = ('pending', 'approved', 'rejected')
        if conv_status not in valid_statuses:
            return Response(
                {"message": f"status noto'g'ri. To'g'ri qiymatlar: {valid_statuses}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        obj = ConversionHistory.objects.create(
            student=student,
            conversion_type=conversion_type,
            amount_from=amount_from,
            amount_to=amount_to,
            som_after=int(data.get('som_after', 0)),
            comment=data.get('comment', ''),
            status=conv_status,
        )

        return Response(
            {"message": "Konvertatsiya tarixi muvaffaqiyatli yaratildi", "data": _serialize_conversion(obj)},
            status=status.HTTP_201_CREATED
        )

    # ── UPDATE ────────────────────────────────────────────────────
    def put(self, request, pk=None):
        if not pk:
            return Response(
                {"message": "pk (id) talab qilinadi"},
                status=status.HTTP_400_BAD_REQUEST
            )

        obj = get_object_or_404(ConversionHistory, pk=pk)
        data = request.data

        if 'student_id' in data:
            obj.student = get_object_or_404(Student, pk=data['student_id'])

        if 'conversion_type' in data:
            valid_types = ('SCORE_TO_COIN', 'SCORE_TO_SOM', 'COIN_TO_SOM')
            if data['conversion_type'] not in valid_types:
                return Response(
                    {"message": f"conversion_type noto'g'ri. To'g'ri qiymatlar: {valid_types}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            obj.conversion_type = data['conversion_type']

        if 'amount_from' in data:
            try:
                obj.amount_from = int(data['amount_from'])
            except (ValueError, TypeError):
                return Response({"message": "amount_from butun son bo'lishi kerak"}, status=400)

        if 'amount_to' in data:
            try:
                obj.amount_to = int(data['amount_to'])
            except (ValueError, TypeError):
                return Response({"message": "amount_to butun son bo'lishi kerak"}, status=400)

        if 'som_after' in data:
            try:
                obj.som_after = int(data['som_after'])
            except (ValueError, TypeError):
                return Response({"message": "som_after butun son bo'lishi kerak"}, status=400)

        if 'comment' in data:
            obj.comment = data['comment']

        if 'status' in data:
            valid_statuses = ('pending', 'approved', 'rejected')
            if data['status'] not in valid_statuses:
                return Response(
                    {"message": f"status noto'g'ri. To'g'ri qiymatlar: {valid_statuses}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            obj.status = data['status']

        obj.save()

        obj.refresh_from_db()
        obj = get_object_or_404(_build_qs(), pk=pk)
        return Response(
            {"message": "Konvertatsiya tarixi muvaffaqiyatli yangilandi", "data": _serialize_conversion(obj)},
            status=status.HTTP_200_OK
        )

    # ── DELETE ────────────────────────────────────────────────────
    def delete(self, request, pk=None):
        if not pk:
            return Response(
                {"message": "pk (id) talab qilinadi"},
                status=status.HTTP_400_BAD_REQUEST
            )
        obj = get_object_or_404(ConversionHistory, pk=pk)
        obj.delete()
        return Response(
            {"message": "Konvertatsiya tarixi o'chirildi"},
            status=status.HTTP_204_NO_CONTENT
        )
