"""
Guruhga taklif oqimi.

Tutor tomoni:
  1. O'quvchini telefon raqami yoki identifikatsiya raqami bo'yicha qidiradi;
  2. Topilgan o'quvchiga guruhga taklif yuboradi (o'quvchi boshqa guruhda bo'lsa - ogohlantirish).

O'quvchi tomoni:
  3. Tizimga kirganda kutayotgan taklifni ko'radi;
  4. Qabul qiladi yoki rad etadi. Qabul qilinsa - boshqa guruhlardan chiqib, shu guruhga qo'shiladi.
"""

from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_user.models import Student

from .helpers import IsStudent, IsTutor, get_student, get_tutor
from .models import TutorGroup, TutorGroupInvitation


def _mask_phone(phone):
    """998944180008 -> +998 ** *** 00 08 (maxfiylik uchun o'rtasi yashiriladi)."""
    if not phone:
        return None
    digits = ''.join(character for character in str(phone) if character.isdigit())
    if len(digits) < 7:
        return f"+{digits}"
    return f"+{digits[:3]} ** *** {digits[-4:-2]} {digits[-2:]}"


def _class_uz(student):
    if not student.class_name:
        return None
    if student.class_name.classes:
        return f"{student.class_name.classes.name}-sinf {student.class_name.name_uz}"
    return student.class_name.name_uz


def _student_payload(student):
    return {
        "id": student.id,
        "full_name": student.full_name,
        "identification": student.identification,
        "phone": _mask_phone(student.user.phone if student.user_id else None),
        "class_uz": _class_uz(student),
        "region": student.region,
        "districts": student.districts,
    }


def _current_group(student, tutor):
    """O'quvchi hozir qaysi tutor guruhida (bo'lsa)."""
    group = TutorGroup.objects.filter(students=student).select_related('tutor').first()
    if group is None:
        return None
    return {
        "id": group.id,
        "name": group.name,
        "tutor_name": group.tutor.full_name,
        "is_mine": group.tutor_id == tutor.id,
    }


def _invitation_payload(invitation, for_student=False):
    data = {
        "id": invitation.id,
        "status": invitation.status,
        "message": invitation.message,
        "created_at": invitation.created_at.strftime("%d/%m/%Y %H:%M"),
        "group": {
            "id": invitation.group_id,
            "name": invitation.group.name,
            "description": invitation.group.description,
        },
    }
    if for_student:
        data["tutor"] = {
            "id": invitation.tutor_id,
            "full_name": invitation.tutor.full_name,
            "identification": invitation.tutor.identification,
        }
    else:
        data["student"] = _student_payload(invitation.student)
    return data


class TutorStudentSearchAPIView(APIView):
    """
    GET /api/v1/tutor/tutor/students/search/?query=<telefon yoki ID>&group_id=<id>

    Tizimdagi istalgan o'quvchini topadi va uni guruhga taklif qilish mumkinligini aytadi.
    `type` parametri ixtiyoriy: 'phone' yoki 'identification'; berilmasa ikkalasi ham sinaladi.
    """
    permission_classes = [IsTutor]

    def get(self, request):
        tutor = get_tutor(request)
        query = (request.GET.get('query') or '').strip()
        search_type = (request.GET.get('type') or '').strip()

        if not query:
            return Response(
                {"detail": "Telefon raqami yoki identifikatsiya raqamini kiriting"},
                status=status.HTTP_400_BAD_REQUEST
            )

        digits = ''.join(character for character in query if character.isdigit())

        lookup = Q()
        if search_type == 'phone':
            if not digits:
                return Response({"found": False, "detail": "Telefon raqami noto'g'ri"},
                                status=status.HTTP_200_OK)
            lookup = Q(user__phone__endswith=digits[-9:])
        elif search_type == 'identification':
            lookup = Q(identification__iexact=query)
        else:
            lookup = Q(identification__iexact=query)
            if digits:
                lookup |= Q(user__phone__endswith=digits[-9:])

        student = (
            Student.objects.filter(lookup)
            .select_related('user', 'class_name', 'class_name__classes')
            .first()
        )

        if student is None:
            return Response(
                {"found": False, "detail": "Bunday o'quvchi topilmadi"},
                status=status.HTTP_200_OK
            )

        group_id = request.GET.get('group_id')
        current_group = _current_group(student, tutor)
        in_this_group = bool(group_id and current_group and str(current_group["id"]) == str(group_id))

        pending = (
            TutorGroupInvitation.objects.filter(
                student=student, status=TutorGroupInvitation.STATUS_PENDING
            )
            .select_related('group', 'tutor')
            .first()
        )
        pending_payload = None
        if pending:
            pending_payload = {
                "id": pending.id,
                "group_name": pending.group.name,
                "tutor_name": pending.tutor.full_name,
                "is_mine": pending.tutor_id == tutor.id,
                "is_same_group": str(pending.group_id) == str(group_id) if group_id else False,
            }

        can_invite = not in_this_group and not (pending_payload and pending_payload["is_same_group"])

        warning = None
        if in_this_group:
            warning = "Bu o'quvchi allaqachon shu guruhda"
        elif pending_payload and pending_payload["is_same_group"]:
            warning = "Bu o'quvchiga taklif allaqachon yuborilgan, javob kutilmoqda"
        elif current_group:
            warning = (
                f"Bu o'quvchi boshqa guruhga qo'shilgan: {current_group['name']}"
                f" ({current_group['tutor_name']}). Taklifni qabul qilsa, shu guruhdan chiqadi."
            )
        elif pending_payload:
            warning = (
                f"Bu o'quvchiga boshqa taklif yuborilgan: {pending_payload['group_name']}"
                f" ({pending_payload['tutor_name']})"
            )

        return Response({
            "found": True,
            "student": _student_payload(student),
            "current_group": current_group,
            "in_this_group": in_this_group,
            "pending_invitation": pending_payload,
            "can_invite": can_invite,
            "warning": warning,
        }, status=status.HTTP_200_OK)


class TutorGroupInvitationListCreateAPIView(APIView):
    """
    GET  /api/v1/tutor/tutor/groups/<pk>/invitations/ - guruhning takliflari
    POST /api/v1/tutor/tutor/groups/<pk>/invitations/ - {student_id, message?} taklif yuborish
    """
    permission_classes = [IsTutor]

    def _get_group(self, request, pk):
        return get_object_or_404(TutorGroup, pk=pk, tutor=get_tutor(request))

    def get(self, request, pk):
        group = self._get_group(request, pk)

        invitations = group.invitations.select_related(
            'student', 'student__user', 'student__class_name', 'student__class_name__classes', 'group'
        )

        status_filter = request.GET.get('status', TutorGroupInvitation.STATUS_PENDING)
        if status_filter and status_filter != 'all':
            invitations = invitations.filter(status=status_filter)

        return Response(
            [_invitation_payload(invitation) for invitation in invitations],
            status=status.HTTP_200_OK
        )

    def post(self, request, pk):
        tutor = get_tutor(request)
        group = self._get_group(request, pk)

        student_id = request.data.get('student_id')
        if not student_id:
            return Response({"error": "student_id talab qilinadi"}, status=status.HTTP_400_BAD_REQUEST)

        student = Student.objects.filter(id=student_id).select_related('user').first()
        if student is None:
            return Response({"error": "O'quvchi topilmadi"}, status=status.HTTP_404_NOT_FOUND)

        if group.students.filter(id=student.id).exists():
            return Response(
                {"error": "Bu o'quvchi allaqachon shu guruhda"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invitation = TutorGroupInvitation.objects.create(
                group=group,
                tutor=tutor,
                student=student,
                message=(request.data.get('message') or '').strip() or None,
            )
        except IntegrityError:
            return Response(
                {"error": "Bu o'quvchiga taklif allaqachon yuborilgan, javob kutilmoqda"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(_invitation_payload(invitation), status=status.HTTP_201_CREATED)


class TutorInvitationCancelAPIView(APIView):
    """DELETE /api/v1/tutor/tutor/invitations/<pk>/ - yuborilgan taklifni bekor qilish."""
    permission_classes = [IsTutor]

    def delete(self, request, pk):
        tutor = get_tutor(request)
        invitation = get_object_or_404(TutorGroupInvitation, pk=pk, tutor=tutor)

        if invitation.status != TutorGroupInvitation.STATUS_PENDING:
            return Response(
                {"error": "Faqat javob kutayotgan taklifni bekor qilish mumkin"},
                status=status.HTTP_400_BAD_REQUEST
            )

        invitation.status = TutorGroupInvitation.STATUS_CANCELLED
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=['status', 'responded_at'])

        return Response({"message": "Taklif bekor qilindi"}, status=status.HTTP_200_OK)


class StudentInvitationListAPIView(APIView):
    """
    GET /api/v1/tutor/student/my-invitations/ - o'quvchining javob kutayotgan takliflari.
    Tizimga kirganda modal ko'rsatish uchun ishlatiladi.
    """
    permission_classes = [IsStudent]

    def get(self, request):
        student = get_student(request)

        invitations = (
            TutorGroupInvitation.objects.filter(
                student=student, status=TutorGroupInvitation.STATUS_PENDING
            )
            .select_related('group', 'tutor')
        )

        return Response(
            [_invitation_payload(invitation, for_student=True) for invitation in invitations],
            status=status.HTTP_200_OK
        )


class StudentInvitationRespondAPIView(APIView):
    """
    POST /api/v1/tutor/student/my-invitations/<pk>/respond/ - {"action": "accept"|"reject"}

    Qabul qilinsa: o'quvchi boshqa barcha tutor guruhlaridan chiqarilib, shu guruhga qo'shiladi.
    """
    permission_classes = [IsStudent]

    def post(self, request, pk):
        student = get_student(request)
        invitation = get_object_or_404(TutorGroupInvitation, pk=pk, student=student)

        if invitation.status != TutorGroupInvitation.STATUS_PENDING:
            return Response(
                {"error": "Bu taklifga allaqachon javob berilgan"},
                status=status.HTTP_400_BAD_REQUEST
            )

        action = (request.data.get('action') or '').strip().lower()
        if action not in ('accept', 'reject'):
            return Response(
                {"error": "action 'accept' yoki 'reject' bo'lishi kerak"},
                status=status.HTTP_400_BAD_REQUEST
            )

        invitation.responded_at = timezone.now()

        if action == 'reject':
            invitation.status = TutorGroupInvitation.STATUS_REJECTED
            invitation.save(update_fields=['status', 'responded_at'])
            return Response({"message": "Taklif rad etildi", "status": invitation.status},
                            status=status.HTTP_200_OK)

        # Bir o'quvchi bir vaqtda faqat bitta guruhda bo'ladi
        for group in TutorGroup.objects.filter(students=student).exclude(pk=invitation.group_id):
            group.students.remove(student)

        invitation.group.students.add(student)
        invitation.status = TutorGroupInvitation.STATUS_ACCEPTED
        invitation.save(update_fields=['status', 'responded_at'])

        return Response({
            "message": "Siz guruhga qo'shildingiz",
            "status": invitation.status,
            "group": {"id": invitation.group_id, "name": invitation.group.name},
        }, status=status.HTTP_200_OK)
