from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from django_app.app_user.models import Teacher, Student
from django_app.app_teacher.models import TeacherFineLog
from django_app.app_student.models import StudentScore


def _get_full_name(user):
    role = getattr(user, 'role', None)
    if role == 'teacher':
        profile = getattr(user, 'teacher_profile', None)
        return getattr(profile, 'full_name', None)
    if role == 'superadmin':
        return f"{user.first_name} {user.last_name}".strip() or user.phone
    return user.phone


def _serialize_fine(fine, show_giver=True):
    student = fine.student
    result = {
        "fine_id":                fine.id,
        "fine_type":              fine.fine_type,
        "fine_type_display":      fine.get_fine_type_display(),
        "amount":                 fine.amount,
        "reason":                 fine.reason,
        "created_at":             fine.created_at.strftime("%d/%m/%Y %H:%M"),
        "student": {
            "id":        student.id,
            "full_name": student.full_name,
            "phone":     student.user.phone,
        },
    }
    if show_giver and fine.given_by:
        result["given_by"] = {
            "id":        fine.given_by.id,
            "phone":     fine.given_by.phone,
            "role":      fine.given_by.role,
            "full_name": _get_full_name(fine.given_by),
        }
    return result


# ─────────────────────────────────────────────────────────────
#  JARIMA QO'YISH (teacher, superadmin) va KO'RISH
# ─────────────────────────────────────────────────────────────
class TeacherFineAPIView(APIView):
    """
    POST /api/v1/teacher/fine/
        Teacher yoki superadmin studentga jarima qo'yadi.
        Body: { "student_id": 5, "fine_type": "score", "amount": 50, "reason": "AI dan ko'chirdi" }

    GET /api/v1/teacher/fine/
        - teacher    → o"zi qo'ygan jarimalar"
        - superadmin → barcha jarimalar (kim qo"ydi, kimga qo'ydi)"
        - student    → o'zi olgan jarimalar
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = getattr(request.user, 'role', None)

        if role == 'teacher':
            qs = TeacherFineLog.objects.select_related(
                'given_by', 'student__user'
            ).filter(given_by=request.user).order_by('-created_at')
            data = [_serialize_fine(f, show_giver=False) for f in qs]
            return Response({"count": len(data), "results": data})

        elif role == 'superadmin':
            qs = TeacherFineLog.objects.select_related(
                'given_by', 'student__user'
            ).order_by('-created_at')

            # Filter: ?student_id=5 yoki ?given_by_id=3
            student_id  = request.GET.get('student_id')
            given_by_id = request.GET.get('given_by_id')
            fine_type   = request.GET.get('fine_type')

            if student_id:
                qs = qs.filter(student__id=student_id)
            if given_by_id:
                qs = qs.filter(given_by__id=given_by_id)
            if fine_type:
                qs = qs.filter(fine_type=fine_type)

            data = [_serialize_fine(f, show_giver=True) for f in qs]
            return Response({"count": len(data), "results": data})

        elif role == 'student':
            student = getattr(request.user, 'student_profile', None)
            if not student:
                return Response({"error": "Student profili topilmadi."}, status=404)
            qs = TeacherFineLog.objects.select_related(
                'given_by', 'student__user'
            ).filter(student=student).order_by('-created_at')
            data = [_serialize_fine(f, show_giver=True) for f in qs]
            return Response({"count": len(data), "results": data})

        return Response({"error": "Ruxsat yo'q."}, status=403)

    def post(self, request):
        role = getattr(request.user, 'role', None)
        if role not in ('teacher', 'superadmin'):
            return Response(
                {"error": "Faqat teacher yoki superadmin jarima qo'ya oladi."},
                status=status.HTTP_403_FORBIDDEN,
            )

        student_id = request.data.get('student_id')
        fine_type  = request.data.get('fine_type')
        amount     = request.data.get('amount')
        reason     = request.data.get('reason', '').strip()

        # Validatsiya
        if not student_id:
            return Response({"error": "student_id talab qilinadi."}, status=400)
        if fine_type not in ('score', 'coin'):
            return Response({"error": "fine_type: 'score' yoki 'coin' bo'lishi kerak."}, status=400)
        try:
            amount = int(amount)
            if amount <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response({"error": "amount musbat butun son bo'lishi kerak."}, status=400)
        if not reason:
            return Response({"error": "reason talab qilinadi."}, status=400)

        try:
            student = Student.objects.select_related('user').get(id=student_id)
        except Student.DoesNotExist:
            return Response({"error": "Student topilmadi."}, status=404)

        with transaction.atomic():
            try:
                score_obj = StudentScore.objects.get(student=student)
            except StudentScore.DoesNotExist:
                return Response({"error": "Student balansi topilmadi."}, status=400)

            if fine_type == 'score':
                if score_obj.score < amount:
                    return Response({
                        "error": f"Ball yetarli emas. Balans: {score_obj.score}, jarima: {amount}."
                    }, status=400)
                score_obj.score -= amount
            else:
                if score_obj.coin < amount:
                    return Response({
                        "error": f"Tanga yetarli emas. Balans: {score_obj.coin}, jarima: {amount}."
                    }, status=400)
                score_obj.coin -= amount

            score_obj.save()

            fine = TeacherFineLog.objects.create(
                given_by=request.user,
                student=student,
                fine_type=fine_type,
                amount=amount,
                reason=reason,
            )

        return Response({
            "detail":         "Jarima muvaffaqiyatli qo'yildi.",
            "fine_id":        fine.id,
            "student":        student.full_name,
            "fine_type":      fine.get_fine_type_display(),
            "amount":         amount,
            "reason":         reason,
            "created_at":     fine.created_at.strftime("%d/%m/%Y %H:%M"),
            "remaining_balance": {
                "score": score_obj.score,
                "coin":  score_obj.coin,
            },
        }, status=status.HTTP_201_CREATED)
