from rest_framework.permissions import BasePermission

class IsTeacher(BasePermission):
    """
    Faqat Teacher rolidagi foydalanuvchilar ko‘ra oladi
    """
    def has_permission(self, request, view):
        # Agar sizda User modelida role degan field bo‘lsa:
        return bool(request.user and request.user.is_authenticated and request.user.role == 'teacher')


