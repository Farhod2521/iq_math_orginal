from rest_framework.permissions import BasePermission

class IsTeacherOrSuperAdmin(BasePermission):
    """
    Teacher va SuperAdmin rollari kira oladi
    """
    def has_permission(self, request, view):
        return bool(
            request.user 
            and request.user.is_authenticated 
            and request.user.role in ['teacher', 'superadmin']
        )
