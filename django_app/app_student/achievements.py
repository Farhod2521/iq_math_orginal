"""
Yutuqlar (Achievement) xizmati.

O'quvchining ko'rsatkichlari mavjud ma'lumotlardan hisoblanadi va admin paneldagi
faol yutuqlar shartlari (condition_type ≥ threshold) bilan solishtiriladi.
Yangi bajarilgan shartlar uchun StudentAchievement yoziladi.

Chaqiriladigan joylar: mavzu testi tekshirilganda, diagnostika tekshirilganda,
o'quvchi tizimga kirganda va yutuqlar ro'yxati so'ralganda.
"""
import logging
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

logger = logging.getLogger(__name__)

MASTERY_SCORE = 80  # mavzu o'zlashtirilgan hisoblanadigan ball


def _local_date(value):
    if value is None:
        return None
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.date()


def activity_dates(student, days=400):
    """O'quvchi faol bo'lgan kunlar: kirish, ball olish, mavzu testi, diagnostika."""
    from django_app.app_user.models import StudentLoginHistory
    from .models import Diagnost_Student, StudentScoreLog, TopicProgress

    since = timezone.now() - timedelta(days=days)
    stamps = []
    stamps += StudentLoginHistory.objects.filter(student=student, login_time__gte=since).values_list("login_time", flat=True)
    stamps += StudentScoreLog.objects.filter(student_score__student=student, awarded_at__gte=since).values_list("awarded_at", flat=True)
    stamps += TopicProgress.objects.filter(user=student, completed_at__gte=since).values_list("completed_at", flat=True)
    stamps += Diagnost_Student.objects.filter(student=student, create_date__gte=since).values_list("create_date", flat=True)
    return {d for d in (_local_date(s) for s in stamps) if d}


def streak_from_dates(dates):
    """Bugun (yoki kecha) bilan tugaydigan ketma-ket faol kunlar soni."""
    today = timezone.localdate()
    day = today if today in dates else today - timedelta(days=1)
    streak = 0
    while day in dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


def _diagnostic_score(diag):
    try:
        return float(((diag.result or {}).get("result") or [{}])[0].get("score") or 0)
    except (AttributeError, IndexError, TypeError, ValueError):
        return 0.0


def subject_mastery_map(student):
    """{subject_id: o'zlashtirilgan mavzular foizi} — har bir fandagi jami mavzularga nisbatan."""
    from django_app.app_teacher.models import Topic
    from .models import TopicProgress

    done = dict(
        TopicProgress.objects.filter(user=student, score__gte=MASTERY_SCORE)
        .values("topic__chapter__subject_id")
        .annotate(n=Count("topic", distinct=True))
        .values_list("topic__chapter__subject_id", "n")
    )
    if not done:
        return {}
    totals = dict(
        Topic.objects.filter(chapter__subject_id__in=done.keys())
        .values("chapter__subject_id")
        .annotate(n=Count("id"))
        .values_list("chapter__subject_id", "n")
    )
    return {sid: min(100, round(n * 100 / totals[sid])) for sid, n in done.items() if totals.get(sid)}


def compute_metrics(student):
    from .models import Diagnost_Student, StudentScore, StudentScoreLog, TopicProgress

    dates = activity_dates(student)
    month_ago = timezone.localdate() - timedelta(days=29)
    score = StudentScore.objects.filter(student=student).first()
    diagnostics = list(Diagnost_Student.objects.filter(student=student).only("result"))

    return {
        "topics_completed": TopicProgress.objects.filter(user=student, score__gte=MASTERY_SCORE).count(),
        "correct_answers": StudentScoreLog.objects.filter(student_score__student=student).count(),
        "streak_days": streak_from_dates(dates),
        "active_days_30": sum(1 for d in dates if d >= month_ago),
        "diagnostics_taken": len(diagnostics),
        "diagnostic_score": round(max((_diagnostic_score(d) for d in diagnostics), default=0)),
        "total_score": score.score if score else 0,
        "total_coins": score.coin if score else 0,
        "subject_mastery": subject_mastery_map(student),
    }


def metric_value(achievement, metrics):
    if achievement.condition_type == "subject_mastery":
        return metrics["subject_mastery"].get(achievement.subject_id, 0) if achievement.subject_id else 0
    return metrics.get(achievement.condition_type, 0) or 0


def check_achievements(student, metrics=None):
    """Bajarilgan, lekin hali berilmagan yutuqlarni beradi. Yangi berilganlar ro'yxatini qaytaradi."""
    from .models import Achievement, StudentAchievement

    earned_ids = set(StudentAchievement.objects.filter(student=student).values_list("achievement_id", flat=True))
    pending = [a for a in Achievement.objects.filter(is_active=True) if a.id not in earned_ids]
    if not pending:
        return []

    metrics = metrics or compute_metrics(student)
    awarded = []
    for achievement in pending:
        if metric_value(achievement, metrics) >= achievement.threshold:
            _, created = StudentAchievement.objects.get_or_create(student=student, achievement=achievement)
            if created:
                awarded.append(achievement)
    return awarded


def check_achievements_safe(student):
    """Asosiy jarayonni (test tekshirish, login) hech qachon buzmasligi uchun."""
    if student is None:
        return []
    try:
        return check_achievements(student)
    except Exception:  # noqa: BLE001
        logger.exception("Yutuqlarni tekshirishda xato (student=%s)", getattr(student, "id", None))
        return []


def achievement_payload(achievement, request=None):
    image = achievement.image.url if achievement.image else ""
    if image and request is not None:
        image = request.build_absolute_uri(image)
    return {
        "id": achievement.id,
        "title_uz": achievement.title_uz,
        "title_ru": achievement.title_ru,
        "description_uz": achievement.description_uz,
        "description_ru": achievement.description_ru,
        "image": image,
        "condition_type": achievement.condition_type,
        "threshold": achievement.threshold,
    }


def student_achievements(student, request=None):
    """Barcha faol yutuqlar: olinganmi, qachon va joriy ko'rsatkich (progress)."""
    from .models import Achievement, StudentAchievement

    metrics = compute_metrics(student)
    check_achievements(student, metrics)
    awarded = {
        sa.achievement_id: sa.awarded_at
        for sa in StudentAchievement.objects.filter(student=student)
    }
    items = []
    for achievement in Achievement.objects.filter(is_active=True).select_related("subject"):
        value = metric_value(achievement, metrics)
        data = achievement_payload(achievement, request)
        data.update({
            "earned": achievement.id in awarded,
            "awarded_at": awarded[achievement.id].isoformat() if achievement.id in awarded else None,
            "value": min(value, achievement.threshold),
            "progress": min(100, round(value * 100 / achievement.threshold)) if achievement.threshold else 100,
        })
        data["_awarded_ts"] = awarded[achievement.id].timestamp() if achievement.id in awarded else 0
        items.append(data)
    # Olinganlar avval (eng yangisi birinchi), keyin progress bo'yicha
    items.sort(key=lambda x: (not x["earned"], -x["_awarded_ts"], -x["progress"]))
    for item in items:
        item.pop("_awarded_ts")
    return items, metrics
