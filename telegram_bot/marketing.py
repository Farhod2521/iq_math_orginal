"""
Marketing: yangi ro'yxatdan o'tgan o'quvchilar haqida xabar.

Har ishga tushganda id si oxirgi yuborilgandan katta o'quvchilar olinadi.
Birinchi ishga tushishda eski o'quvchilar yuborilmaydi — hisob shu paytdan boshlanadi.
"""
import html
import logging

from django.utils import timezone

from . import config, state
from .telegram_api import broadcast

logger = logging.getLogger(__name__)

BATCH_LIMIT = 30  # bir martada ko'pi bilan shuncha xabar (qolgani keyingi daqiqada)


def _esc(value):
    return html.escape(str(value)) if value not in (None, "") else "—"


def _referral(student):
    """O'quvchi kimning referal havolasi orqali kelgan"""
    from django_app.app_student.models import StudentReferralTransaction
    from django_app.app_tutor.models import TutorReferralTransaction

    tutor_ref = TutorReferralTransaction.objects.filter(student=student).select_related("tutor").first()
    if tutor_ref:
        return f"O'qituvchi: {tutor_ref.tutor.full_name} ({tutor_ref.tutor.identification})"
    student_ref = StudentReferralTransaction.objects.filter(student=student).select_related("by_student").first()
    if student_ref:
        return f"O'quvchi: {student_ref.by_student.full_name} ({student_ref.by_student.identification})"
    return None


def _parents(student):
    from django_app.app_user.models import ParentStudentRelation

    relations = (
        ParentStudentRelation.objects.filter(student=student, is_confirmed=True)
        .select_related("parent__user")
    )
    return [f"{rel.parent.full_name} (+{rel.parent.user.phone})" for rel in relations]


def format_student(student):
    from django_app.app_user.VIEW.parent_child_account import is_virtual_phone

    user = student.user
    joined = timezone.localtime(user.date_joined).strftime("%d.%m.%Y %H:%M") if user.date_joined else None
    phone = "telefonsiz (ota-ona yaratgan)" if is_virtual_phone(user.phone) else f"+{user.phone}"
    region = ", ".join(part for part in (student.region, student.districts) if part)

    lines = [
        "🆕 <b>Yangi o'quvchi ro'yxatdan o'tdi</b>",
        "",
        f"👤 <b>{_esc(student.full_name)}</b>",
        f"📞 Telefon: {_esc(phone)}",
        f"🎓 Sinf: {_esc(student.class_name.name if student.class_name else None)}",
        f"🆔 ID: <code>{_esc(student.identification)}</code>",
        f"🌐 Til: {_esc((student.lang or '').upper())}  •  Qurilma: {_esc(user.device)}",
        f"🕒 Sana: {_esc(joined)}",
    ]
    if region:
        lines.append(f"📍 Hudud: {_esc(region)}")
    referral = _referral(student)
    if referral:
        lines.append(f"🔗 Referal: {_esc(referral)}")
    parents = _parents(student)
    if parents:
        lines.append(f"👨‍👩‍👦 Ota-ona: {_esc(', '.join(parents))}")
    return "\n".join(lines)


def notify_new_students():
    """Yangi o'quvchilarni marketing chatlariga yuboradi. Yuborilganlar sonini qaytaradi."""
    from django_app.app_user.models import Student

    if not config.BOT_TOKEN or not config.MARKETING_CHAT_IDS:
        return 0

    last_id = state.load().get("last_student_id")
    if last_id is None:
        # Birinchi ishga tushish: eski o'quvchilarni yubormaymiz
        latest = Student.objects.order_by("-id").values_list("id", flat=True).first() or 0
        state.save(last_student_id=latest)
        logger.info("Marketing: hisob o'quvchi id=%s dan boshlandi", latest)
        return 0

    students = list(
        Student.objects.filter(id__gt=last_id)
        .select_related("user", "class_name")
        .order_by("id")[:BATCH_LIMIT]
    )
    sent = 0
    for student in students:
        if not broadcast(config.MARKETING_CHAT_IDS, format_student(student)):
            # Hech bir chatga ketmadi (Telegram ishlamayapti) — keyingi daqiqada shu o'quvchidan davom etamiz
            break
        state.save(last_student_id=student.id)
        sent += 1
    return sent
