from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django.shortcuts import get_object_or_404

from django_app.app_student.models import Diagnost_Student


class IsSuperAdminOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and getattr(request.user, "role", None) in ("superadmin", "admin")
        )


def _serialize_diagnost(d):
    return {
        "id": d.id,
        "student_id": d.student.id,
        "student_name": d.student.full_name,
        "subject_id": d.subject.id if d.subject else None,
        "subject_name_uz": d.subject.name_uz if d.subject else None,
        "subject_name_ru": d.subject.name_ru if d.subject else None,
        "level": d.level,
        "result": d.result,
        "chapters": list(d.chapters.values_list("id", flat=True)),
        "topics": list(d.topic.values_list("id", flat=True)),
        "create_date": (
            d.create_date.strftime("%d/%m/%Y %H:%M") if d.create_date else None
        ),
    }


# ════════════════════════════════════════════════════════
#  SUPERADMIN — Diagnost_Student CRUD
#  GET    /api/v1/superadmin/diagnost/
#  GET    /api/v1/superadmin/diagnost/<pk>/
#  DELETE /api/v1/superadmin/diagnost/<pk>/
# ════════════════════════════════════════════════════════
class SuperAdminDiagnostCRUDAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    # ── LIST / DETAIL ─────────────────────────────────
    def get(self, request, pk=None):
        if pk:
            d = get_object_or_404(
                Diagnost_Student.objects.select_related("student", "subject")
                .prefetch_related("chapters", "topic"),
                pk=pk,
            )
            return Response(_serialize_diagnost(d))

        qs = (
            Diagnost_Student.objects
            .select_related("student", "subject")
            .prefetch_related("chapters", "topic")
            .order_by("-id")
        )

        # Filter: ?student_id=12
        student_id = request.query_params.get("student_id")
        if student_id:
            qs = qs.filter(student_id=student_id)

        # Filter: ?subject_id=3
        subject_id = request.query_params.get("subject_id")
        if subject_id:
            qs = qs.filter(subject_id=subject_id)

        # Filter: ?level=2
        level = request.query_params.get("level")
        if level:
            qs = qs.filter(level=level)

        # Search: ?search=Ali
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(student__full_name__icontains=search)

        results = [_serialize_diagnost(d) for d in qs]
        return Response({"count": len(results), "results": results})

    # ── DELETE ────────────────────────────────────────
    def delete(self, request, pk):
        d = get_object_or_404(Diagnost_Student, pk=pk)
        d.delete()
        return Response(
            {"message": "Diagnostika o'chirildi"},
            status=status.HTTP_204_NO_CONTENT,
        )
