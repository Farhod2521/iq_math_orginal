# permissions.py
from rest_framework.permissions import BasePermission


class IsTeacher(BasePermission):
    message = "Faqat o‘qituvchilar bu amalni bajarishi mumkin."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == "teacher"
        )
