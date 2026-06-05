from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

User = get_user_model()

ACTION_LABELS = {1: "qo'shildi", 2: "o'zgartirildi", 3: "o'chirildi"}


class IsSuperAdminOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and getattr(request.user, "role", None) in ("superadmin", "admin")
        )


def _serialize(log):
    return {
        "id": log.id,
        "action_time": log.action_time.strftime("%d/%m/%Y %H:%M"),
        "user_id": log.user_id,
        "user": log.user.get_full_name() or log.user.phone,
        "content_type_id": log.content_type_id,
        "content_type": log.content_type.model if log.content_type else None,
        "object_id": log.object_id,
        "object_repr": log.object_repr,
        "action_flag": log.action_flag,
        "action_label": ACTION_LABELS.get(log.action_flag, ""),
        "change_message": log.get_change_message(),
    }


# ════════════════════════════════════════════════════════
#  GET    /api/v1/superadmin/log-entries/
#  GET    /api/v1/superadmin/log-entries/<pk>/
#  POST   /api/v1/superadmin/log-entries/
#  DELETE /api/v1/superadmin/log-entries/<pk>/
#  DELETE /api/v1/superadmin/log-entries/?user_id=1
#  DELETE /api/v1/superadmin/log-entries/?action_flag=3
# ════════════════════════════════════════════════════════
class LogEntryCRUDAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    # ── LIST / DETAIL ─────────────────────────────────
    def get(self, request, pk=None):
        if pk:
            log = get_object_or_404(
                LogEntry.objects.select_related("user", "content_type"), pk=pk
            )
            return Response(_serialize(log))

        qs = LogEntry.objects.select_related(
            "user", "content_type"
        ).order_by("-action_time")

        # Filter: ?user_id=1
        user_id = request.query_params.get("user_id")
        if user_id:
            qs = qs.filter(user_id=user_id)

        # Filter: ?action_flag=2  (1=qo'shish, 2=o'zgartirish, 3=o'chirish)
        action_flag = request.query_params.get("action_flag")
        if action_flag:
            qs = qs.filter(action_flag=action_flag)

        # Filter: ?content_type=student
        content_type = request.query_params.get("content_type")
        if content_type:
            qs = qs.filter(content_type__model__icontains=content_type)

        # Pagination: ?page=1&limit=10
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1
        try:
            limit = max(1, int(request.query_params.get("limit", 10)))
        except ValueError:
            limit = 10

        total_count = qs.count()          # filter dan keyin, limit dan oldin
        offset = (page - 1) * limit
        page_qs = qs[offset: offset + limit]

        # next / previous URL larini qurish
        def build_url(p):
            params = request.query_params.copy()
            params["page"] = p
            params["limit"] = limit
            return request.build_absolute_uri(
                "?" + "&".join(f"{k}={v}" for k, v in params.items())
            )

        next_url = build_url(page + 1) if offset + limit < total_count else None
        prev_url = build_url(page - 1) if page > 1 else None

        results = [_serialize(log) for log in page_qs]
        return Response({
            "count": total_count,
            "next": next_url,
            "previous": prev_url,
            "results": results,
        })

    # ── CREATE ────────────────────────────────────────
    def post(self, request, pk=None):
        data = request.data

        required = ["user_id", "content_type_id", "object_id", "object_repr", "action_flag"]
        for field in required:
            if not data.get(field):
                return Response(
                    {"error": f"{field} majburiy"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        action_flag = int(data["action_flag"])
        if action_flag not in (1, 2, 3):
            return Response(
                {"error": "action_flag faqat 1, 2 yoki 3 bo'lishi mumkin"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=data["user_id"])
        except User.DoesNotExist:
            return Response({"error": "User topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        try:
            content_type = ContentType.objects.get(pk=data["content_type_id"])
        except ContentType.DoesNotExist:
            return Response(
                {"error": "ContentType topilmadi"}, status=status.HTTP_404_NOT_FOUND
            )

        log = LogEntry.objects.create(
            user=user,
            content_type=content_type,
            object_id=str(data["object_id"]),
            object_repr=str(data["object_repr"]),
            action_flag=action_flag,
            change_message=data.get("change_message", ""),
        )
        return Response(_serialize(log), status=status.HTTP_201_CREATED)

    # ── DELETE (bitta yoki ommaviy) ───────────────────
    def delete(self, request, pk=None):
        # Bitta o'chirish
        if pk:
            log = LogEntry.objects.filter(pk=pk).first()
            if not log:
                return Response(
                    {"error": "Log yozuv topilmadi"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            log.delete()
            return Response({"success": "Log yozuv o'chirildi"})

        # Ommaviy o'chirish
        user_id = request.query_params.get("user_id")
        action_flag = request.query_params.get("action_flag")

        if not user_id and not action_flag:
            return Response(
                {"error": "Ommaviy o'chirish uchun kamida ?user_id yoki ?action_flag kerak"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = LogEntry.objects.all()
        if user_id:
            qs = qs.filter(user_id=user_id)
        if action_flag:
            qs = qs.filter(action_flag=action_flag)

        count, _ = qs.delete()
        return Response({"success": f"{count} ta log o'chirildi"})
