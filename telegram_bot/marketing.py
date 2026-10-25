"""
Marketing chatiga xabarlar (har daqiqada, Celery):
  🆕 yangi ro'yxatdan o'tgan o'quvchi
  💳 muvaffaqiyatli to'lov (alohida belgi bilan)
  📝 "Bepul darsga yoziling" arizasi
Har xabar oxirida 7 va 30 kunlik statistika (ro'yxatdan o'tganlar, obunalar, arizalar).

Har ishga tushganda oxirgi yuborilgandan keyingi yozuvlar olinadi.
Birinchi ishga tushishda eskilari yuborilmaydi — hisob shu paytdan boshlanadi.
"""
import html
import logging
from datetime import timedelta

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


def stats_footer():
    """7 va 30 kunlik ko'rsatkichlar: ro'yxatdan o'tganlar, obuna sotib olganlar, bepul darsga arizalar."""
    from django_app.app_management.models import FreeLessonRequest
    from django_app.app_payments.models import Payment
    from django_app.app_user.models import Student

    now = timezone.now()
    d7, d30 = now - timedelta(days=7), now - timedelta(days=30)

    def students(since):
        return Student.objects.filter(user__date_joined__gte=since).count()

    def subscribers(since):
        return (
            Payment.objects.filter(status="success", payment_date__gte=since)
            .values("student").distinct().count()
        )

    def leads(since):
        return FreeLessonRequest.objects.filter(created_at__gte=since).count()

    return "\n".join([
        "",
        "📊 <b>Statistika</b>",
        f"👥 Ro'yxatdan o'tganlar: 7 kunda — <b>{students(d7)} ta</b>, 30 kunda — <b>{students(d30)} ta</b>",
        f"💳 Obuna: 7 kunda — <b>{subscribers(d7)} ta</b>, 30 kunda — <b>{subscribers(d30)} ta</b>",
        f"📝 Bepul darsga arizalar: 7 kunda — <b>{leads(d7)} ta</b>, 30 kunda — <b>{leads(d30)} ta</b>",
    ])


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
    lines.append(stats_footer())
    return "\n".join(lines)


def format_payment(payment, resolve_tariff):
    """To'lov xabari — alohida 💳 belgisi bilan."""
    from django_app.app_user.VIEW.parent_child_account import is_virtual_phone

    student = payment.student
    user = student.user
    phone = "telefonsiz (ota-ona yaratgan)" if is_virtual_phone(user.phone) else f"+{user.phone}"
    tariff, _ = resolve_tariff(payment)
    period = f"{payment.subscription_months} oylik"
    paid_at = timezone.localtime(payment.payment_date).strftime("%d.%m.%Y %H:%M") if payment.payment_date else None
    amount = f"{int(round(float(payment.amount or 0))):,}".replace(",", " ")

    lines = [
        "💳✅ <b>TO'LOV QILINDI</b>",
        "",
        f"👤 <b>{_esc(student.full_name)}</b>",
        f"📞 Telefon: {_esc(phone)}",
        f"🎓 Sinf: {_esc(student.class_name.name if student.class_name else None)}",
        f"📦 Tarif: <b>{_esc(f'{tariff} — {period}' if tariff else period)}</b>",
        f"💰 Summa: <b>{amount} so'm</b>",
    ]
    if payment.coupon_id:
        lines.append(f"🎟 Kupon: {_esc(payment.coupon.code)} (-{payment.discount_percent}%)")
    if payment.paid_by_parent_id:
        lines.append(f"👨‍👩‍👦 To'lagan ota-ona: {_esc(payment.paid_by_parent.full_name)}")
    if payment.payment_gateway:
        lines.append(f"🏦 To'lov tizimi: {_esc(payment.payment_gateway)}")
    lines.append(f"🕒 Sana: {_esc(paid_at)}")
    lines.append(stats_footer())
    return "\n".join(lines)


def format_lead(lead):
    created = timezone.localtime(lead.created_at).strftime("%d.%m.%Y %H:%M")
    lines = [
        "📝 <b>Bepul darsga yangi ariza</b>",
        "",
        f"👤 Ota-ona: <b>{_esc(lead.parent_name)}</b>",
        f"📞 Telefon: +{_esc(lead.phone)}",
        f"🎓 Farzand sinfi: {_esc(f'{lead.class_num}-sinf' if lead.class_num else None)}",
        f"🕒 Sana: {_esc(created)}",
        "",
        "☎️ Iltimos, qo'ng'iroq qiling va mentor panelidagi \"Arizalar\" bo'limida holatini belgilang.",
    ]
    lines.append(stats_footer())
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


def notify_new_payments():
    """Yangi muvaffaqiyatli to'lovlarni marketing chatiga yuboradi (payment_date bo'yicha)."""
    from django_app.app_payments.models import Payment
    from django_app.app_user.VIEW.monthly_report_view import _tariff_resolver

    if not config.BOT_TOKEN or not config.MARKETING_CHAT_IDS:
        return 0

    last_id = state.load().get("last_payment_id")
    if last_id is None:
        # Birinchi ishga tushish: eski to'lovlarni yubormaymiz
        latest = Payment.objects.filter(status="success").order_by("-id").values_list("id", flat=True).first() or 0
        state.save(last_payment_id=latest, sent_payment_ids=[])
        return 0

    # To'lov "pending" holatida yaratilib, keyinroq "success" bo'ladi — shuning uchun id bo'yicha emas,
    # oxirgi 2 kundagi muvaffaqiyatli to'lovlardan hali yuborilmaganlari olinadi
    sent_ids = set(state.load().get("sent_payment_ids") or [])
    payments = list(
        Payment.objects.filter(
            status="success",
            payment_date__gte=timezone.now() - timedelta(days=2),
            id__gt=last_id,  # bot yoqilishidan oldingi to'lovlar yuborilmaydi
        )
        .exclude(id__in=sent_ids)
        .select_related("student__user", "student__class_name", "coupon", "paid_by_parent")
        .order_by("payment_date")[:BATCH_LIMIT]
    )
    if not payments:
        return 0
    resolve = _tariff_resolver()
    sent = 0
    for payment in payments:
        if not broadcast(config.MARKETING_CHAT_IDS, format_payment(payment, resolve)):
            break
        sent_ids.add(payment.id)
        # Ro'yxat cheksiz o'smasin — oxirgi 500 tasi yetarli
        state.save(sent_payment_ids=sorted(sent_ids)[-500:])
        sent += 1
    return sent


def notify_new_leads():
    """Yangi "Bepul darsga yoziling" arizalarini marketing chatiga yuboradi."""
    from django_app.app_management.models import FreeLessonRequest

    if not config.BOT_TOKEN or not config.MARKETING_CHAT_IDS:
        return 0

    last_id = state.load().get("last_lead_id")
    if last_id is None:
        # Arizalar yangi bo'lim — birinchi ishga tushishda ham mavjudlari yuboriladi
        last_id = 0

    leads = list(FreeLessonRequest.objects.filter(id__gt=last_id).order_by("id")[:BATCH_LIMIT])
    sent = 0
    for lead in leads:
        if not broadcast(config.MARKETING_CHAT_IDS, format_lead(lead)):
            break
        state.save(last_lead_id=lead.id)
        sent += 1
    return sent
