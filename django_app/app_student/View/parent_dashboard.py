"""
Ota-ona bosh sahifasi (dashboard/parent/home) uchun API'lar.

GET /api/v1/func_student/parent/dashboard/?period=month|all&child=<id>
    Kartalar, farzandlar, fanlar natijasi, 30 kunlik faollik, so'nggi faoliyatlar,
    top mavzular va yutuqlar — bitta so'rovda.
GET /api/v1/func_student/achievements/?student=<id>
    Barcha yutuqlar (olingan/olinmagan + progress). O'quvchi o'zinikini,
    ota-ona esa tasdiqlangan farzandiniki ko'radi.
"""
from collections import defaultdict
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_student.achievements import (
    activity_dates,
    check_achievements_safe,
    student_achievements,
)
from django_app.app_student.models import (
    Diagnost_Student,
    StudentAchievement,
    StudentScore,
    StudentScoreLog,
    TopicProgress,
)
from django_app.app_user.models import ParentStudentRelation, Student

RECENT_LIMIT = 8
TOP_TOPICS_LIMIT = 6


def _parent_children(user):
    parent = getattr(user, "parent_profile", None)
    if parent is None:
        return None, []
    children = list(
        Student.objects.filter(parent_relations__parent=parent, parent_relations__is_confirmed=True)
        .select_related("class_name__classes")
        .distinct()
        .order_by("id")
    )
    return parent, children


def _class_name(student):
    subject = student.class_name
    if subject is not None and getattr(subject, "classes", None) is not None:
        return subject.classes.name
    return ""


def _is_active(student):
    try:
        subscription = student.subscription
    except Exception:  # noqa: BLE001 — obuna yo'q
        return False
    return bool(subscription and subscription.end_date and subscription.end_date >= timezone.now())


def _percent(part, whole):
    return round(part * 100 / whole) if whole else 0


def _diag_score(diag):
    try:
        return round(float(((diag.result or {}).get("result") or [{}])[0].get("score") or 0))
    except (AttributeError, IndexError, TypeError, ValueError):
        return 0


def _subject_scores(student_ids, since=None):
    """Fanlar bo'yicha o'rtacha ball (ishlangan mavzular bo'yicha), fan nomi bilan."""
    qs = TopicProgress.objects.filter(user_id__in=student_ids)
    if since is not None:
        qs = qs.filter(completed_at__gte=since)
    return list(
        qs.values(
            "user_id",
            "topic__chapter__subject_id",
            "topic__chapter__subject__name_uz",
            "topic__chapter__subject__name_ru",
            "topic__chapter__subject__classes__name",
        )
        .annotate(avg=Avg("score"), topics=Count("topic", distinct=True))
        .order_by("-topics")
    )


def _rank_in_class(student, score_map):
    """O'quvchining sinfdagi o'rni (ball bo'yicha) va sinfdagi o'quvchilar soni."""
    class_obj = getattr(student.class_name, "classes", None) if student.class_name else None
    if class_obj is None:
        return None
    classmates = StudentScore.objects.filter(student__class_name__classes=class_obj)
    total = classmates.count()
    if not total:
        return None
    own = score_map.get(student.id, 0)
    rank = classmates.filter(score__gt=own).count() + 1
    return {"rank": rank, "total": total}


class ParentDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        parent, children = _parent_children(request.user)
        if parent is None:
            return Response({"detail": "Faqat ota-onalar uchun."}, status=status.HTTP_403_FORBIDDEN)

        child_param = request.query_params.get("child")
        scope = [c for c in children if str(c.id) == str(child_param)] if child_param else children
        ids = [c.id for c in scope]
        names = {c.id: c.full_name for c in children}
        period = request.query_params.get("period", "month")

        now = timezone.now()
        month_ago = now - timedelta(days=30)
        two_months_ago = now - timedelta(days=60)
        today = timezone.localdate()

        # Yutuqlar har so'rovda yangilanadi (shart bajarilgan bo'lsa beriladi)
        for child in scope:
            check_achievements_safe(child)

        # ---- Farzandlar kartalari: har biri bo'yicha 3 ta asosiy fan ----
        per_child_subjects = defaultdict(list)
        all_subject_rows = _subject_scores(ids)
        for row in all_subject_rows:
            per_child_subjects[row["user_id"]].append({
                "id": row["topic__chapter__subject_id"],
                "name_uz": row["topic__chapter__subject__name_uz"],
                "name_ru": row["topic__chapter__subject__name_ru"],
                "class_name": row["topic__chapter__subject__classes__name"] or "",
                "percent": round(row["avg"] or 0),
            })

        score_map = dict(StudentScore.objects.filter(student_id__in=ids).values_list("student_id", "score"))
        children_data = []
        best_rank = None
        for child in scope:
            rank = _rank_in_class(child, score_map)
            if rank and (best_rank is None or rank["rank"] < best_rank["rank"]):
                best_rank = {**rank, "child_name": child.full_name}
            children_data.append({
                "id": child.id,
                "full_name": child.full_name,
                "class_name": _class_name(child),
                "is_active": _is_active(child),
                "subjects": per_child_subjects.get(child.id, [])[:3],
                "rating": rank,
            })

        # ---- Fanlar bo'yicha umumiy natija (bir xil nomli fanlar birlashtiriladi) ----
        period_rows = _subject_scores(ids, since=month_ago if period == "month" else None)
        merged = {}
        for row in period_rows:
            key = (row["topic__chapter__subject__name_uz"] or "").strip().lower()
            item = merged.setdefault(key, {
                "name_uz": row["topic__chapter__subject__name_uz"],
                "name_ru": row["topic__chapter__subject__name_ru"],
                "sum": 0,
                "topics": 0,
            })
            item["sum"] += (row["avg"] or 0) * row["topics"]
            item["topics"] += row["topics"]
        subjects_overall = sorted(
            (
                {"name_uz": v["name_uz"], "name_ru": v["name_ru"], "percent": round(v["sum"] / v["topics"])}
                for v in merged.values() if v["topics"]
            ),
            key=lambda x: -x["percent"],
        )

        # ---- Faollik: faol kunlar foizi (oxirgi 30 kun va undan oldingi 30 kun) ----
        this_period, prev_period = [], []
        for child in scope:
            dates = activity_dates(child, days=60)
            this_period.append(sum(1 for d in dates if d > today - timedelta(days=30)))
            prev_period.append(sum(1 for d in dates if today - timedelta(days=60) < d <= today - timedelta(days=30)))
        activity_now = _percent(sum(this_period), 30 * len(scope)) if scope else 0
        activity_prev = _percent(sum(prev_period), 30 * len(scope)) if scope else 0

        # ---- Yechilgan misollar (to'g'ri javoblar) ----
        logs = StudentScoreLog.objects.filter(student_score__student_id__in=ids)
        solved_now = logs.filter(awarded_at__gte=month_ago).count()
        solved_prev = logs.filter(awarded_at__gte=two_months_ago, awarded_at__lt=month_ago).count()

        daily = dict(
            logs.filter(awarded_at__gte=now - timedelta(days=30))
            .annotate(day=TruncDate("awarded_at"))
            .values("day")
            .annotate(n=Count("id"))
            .values_list("day", "n")
        )
        activity_days = [
            {"date": (today - timedelta(days=offset)).isoformat(), "count": daily.get(today - timedelta(days=offset), 0)}
            for offset in range(29, -1, -1)
        ]

        # ---- So'nggi faoliyatlar ----
        recent = []
        for tp in (
            TopicProgress.objects.filter(user_id__in=ids, completed_at__isnull=False)
            .select_related("topic__chapter__subject")
            .order_by("-completed_at")[:RECENT_LIMIT]
        ):
            subject = tp.topic.chapter.subject if tp.topic and tp.topic.chapter else None
            recent.append({
                "type": "topic_test",
                "child": names.get(tp.user_id, ""),
                "title_uz": tp.topic.name_uz if tp.topic else "",
                "title_ru": tp.topic.name_ru if tp.topic else "",
                "subject_uz": subject.name_uz if subject else "",
                "subject_ru": subject.name_ru if subject else "",
                "value": round(tp.score),
                "at": tp.completed_at.isoformat(),
            })
        for diag in (
            Diagnost_Student.objects.filter(student_id__in=ids, create_date__isnull=False)
            .select_related("subject")
            .order_by("-create_date")[:RECENT_LIMIT]
        ):
            recent.append({
                "type": "diagnostic",
                "child": names.get(diag.student_id, ""),
                "title_uz": diag.subject.name_uz if diag.subject else "",
                "title_ru": diag.subject.name_ru if diag.subject else "",
                "subject_uz": "",
                "subject_ru": "",
                "value": _diag_score(diag),
                "at": diag.create_date.isoformat(),
            })
        for award in (
            StudentAchievement.objects.filter(student_id__in=ids)
            .select_related("achievement")
            .order_by("-awarded_at")[:RECENT_LIMIT]
        ):
            recent.append({
                "type": "achievement",
                "child": names.get(award.student_id, ""),
                "title_uz": award.achievement.title_uz,
                "title_ru": award.achievement.title_ru,
                "subject_uz": award.achievement.description_uz,
                "subject_ru": award.achievement.description_ru,
                "value": None,
                "at": award.awarded_at.isoformat(),
            })
        recent.sort(key=lambda x: x["at"], reverse=True)
        recent = recent[:RECENT_LIMIT]

        # ---- Top mavzular ----
        top_topics, seen = [], set()
        for tp in (
            TopicProgress.objects.filter(user_id__in=ids, score__gt=0)
            .select_related("topic__chapter__subject")
            .order_by("-score", "-completed_at")[:40]
        ):
            if not tp.topic or tp.topic_id in seen:
                continue
            seen.add(tp.topic_id)
            subject = tp.topic.chapter.subject if tp.topic.chapter else None
            top_topics.append({
                "topic_uz": tp.topic.name_uz,
                "topic_ru": tp.topic.name_ru,
                "subject_uz": subject.name_uz if subject else "",
                "subject_ru": subject.name_ru if subject else "",
                "percent": round(tp.score),
            })
            if len(top_topics) >= TOP_TOPICS_LIMIT:
                break

        # ---- Yutuqlar: tanlangan (yoki birinchi) farzand bo'yicha ----
        focus = scope[0] if scope else None
        achievements = student_achievements(focus, request)[0] if focus else []

        subject_names = []
        for row in all_subject_rows:
            name = {"name_uz": row["topic__chapter__subject__name_uz"], "name_ru": row["topic__chapter__subject__name_ru"]}
            if name not in subject_names:
                subject_names.append(name)

        return Response({
            "parent": {"full_name": parent.full_name},
            "summary": {
                "children_count": len(scope),
                "subjects": subject_names,
                "activity": {"percent": activity_now, "delta": activity_now - activity_prev},
                "solved": {"count": solved_now, "delta": solved_now - solved_prev},
                "rating": best_rank,
            },
            "children": children_data,
            "subjects_overall": subjects_overall,
            "activity_days": activity_days,
            "recent": recent,
            "top_topics": top_topics,
            "achievements": achievements,
            "achievements_child": {"id": focus.id, "full_name": focus.full_name} if focus else None,
        })


class StudentAchievementsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        student_id = request.query_params.get("student")
        student = None
        if student_id and getattr(user, "parent_profile", None) is not None:
            relation = ParentStudentRelation.objects.filter(
                parent=user.parent_profile, student_id=student_id, is_confirmed=True
            ).select_related("student").first()
            student = relation.student if relation else None
        elif getattr(user, "student_profile", None) is not None:
            student = user.student_profile

        if student is None:
            return Response({"detail": "O'quvchi topilmadi."}, status=status.HTTP_404_NOT_FOUND)

        items, metrics = student_achievements(student, request)
        metrics.pop("subject_mastery", None)
        return Response({
            "student": {"id": student.id, "full_name": student.full_name},
            "earned_count": sum(1 for item in items if item["earned"]),
            "total": len(items),
            "metrics": metrics,
            "achievements": items,
        })


# ---------------------------------------------------------------------------
# Farzand sahifasi: GET /api/v1/func_student/parent/children/<id>/overview/
# ---------------------------------------------------------------------------

def _duration_seconds(student, since=None):
    """Testlarda sarflangan vaqt: mavzu testlari (result JSON) + diagnostikalar."""
    total = 0
    topic_qs = TopicProgress.objects.filter(user=student, result__isnull=False)
    if since is not None:
        topic_qs = topic_qs.filter(completed_at__gte=since)
    for result in topic_qs.values_list("result", flat=True):
        if isinstance(result, dict):
            if since is None:
                total += result.get("total_duration_seconds") or 0
            else:
                total += (result.get("last_attempt") or {}).get("duration_seconds") or 0
    diag_qs = Diagnost_Student.objects.filter(student=student)
    if since is not None:
        diag_qs = diag_qs.filter(create_date__gte=since)
    for result in diag_qs.values_list("result", flat=True):
        if isinstance(result, dict):
            total += result.get("duration_seconds") or 0
    return int(total)


def _recent_item(kind, at, title_uz="", title_ru="", subject_uz="", subject_ru="", value=None):
    return {
        "type": kind,
        "title_uz": title_uz or "",
        "title_ru": title_ru or "",
        "subject_uz": subject_uz or "",
        "subject_ru": subject_ru or "",
        "value": value,
        "at": at.isoformat(),
    }


class ParentChildOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        from django_app.app_payments.models import Payment
        from django_app.app_teacher.models import Topic
        from django_app.app_user.device_service import serialize_device
        from django_app.app_user.models import StudentLoginHistory, Subject, UserDevice

        parent = getattr(request.user, "parent_profile", None)
        relation = None
        if parent is not None:
            relation = (
                ParentStudentRelation.objects.filter(parent=parent, student_id=student_id, is_confirmed=True)
                .select_related("student__user", "student__class_name__classes")
                .first()
            )
        if relation is None:
            return Response({"detail": "Farzand topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        child = relation.student
        check_achievements_safe(child)

        now = timezone.now()
        today = timezone.localdate()
        month_ago = now - timedelta(days=30)
        two_months_ago = now - timedelta(days=60)
        class_obj = getattr(child.class_name, "classes", None) if child.class_name else None

        # ---- Profil ----
        last_login = StudentLoginHistory.objects.filter(student=child).order_by("-login_time").first()
        profile = {
            "id": child.id,
            "full_name": child.full_name,
            "identification": child.identification,
            "class_name": class_obj.name if class_obj else "",
            "is_active": _is_active(child),
            "registered_at": child.user.date_joined.isoformat() if child.user.date_joined else None,
            "last_login": last_login.login_time.isoformat() if last_login else None,
            "study_time_seconds": _duration_seconds(child),
        }

        # ---- Obuna va to'lovlar ----
        payments = Payment.objects.filter(student=child, status="success").order_by("-payment_date", "-created_at")
        last_payment = payments.first()
        try:
            sub = child.subscription
        except Exception:  # noqa: BLE001 — obuna yo'q
            sub = None
        subscription = None
        if sub is not None:
            # Joriy tarif davri: tugash sanasidan tarif oylari ayiriladi (obuna yaratilgan sana emas)
            months = last_payment.subscription_months if last_payment else None
            period_start = sub.start_date
            if months and sub.end_date:
                period_start = max(sub.start_date or sub.end_date, sub.end_date - timedelta(days=30 * months))
            total_days = max(1, (sub.end_date - period_start).days) if period_start and sub.end_date else 0
            subscription = {
                "is_active": bool(sub.end_date and sub.end_date >= now),
                "is_paid": sub.is_paid,
                "start_date": period_start.isoformat() if period_start else None,
                "end_date": sub.end_date.isoformat() if sub.end_date else None,
                "next_payment_date": sub.next_payment_date.isoformat() if sub.next_payment_date else None,
                "days_left": max(0, (sub.end_date - now).days) if sub.end_date else 0,
                "total_days": total_days,
                "months": last_payment.subscription_months if last_payment else None,
            }
        payment_info = {
            "last_amount": float(last_payment.amount) if last_payment else 0,
            "last_date": (last_payment.payment_date or last_payment.created_at).isoformat() if last_payment else None,
            "total_paid": float(sum(p.amount for p in payments)),
            "count": payments.count(),
        }

        # ---- Fanlar natijasi ----
        rows = list(
            TopicProgress.objects.filter(user=child)
            .values(
                "topic__chapter__subject_id",
                "topic__chapter__subject__name_uz",
                "topic__chapter__subject__name_ru",
                "topic__chapter__subject__classes__name",
            )
            .annotate(
                avg=Avg("score"),
                tests=Count("topic", distinct=True),
                done=Count("topic", filter=Q(score__gte=80), distinct=True),
            )
            .order_by("-tests")
        )
        subject_ids = [r["topic__chapter__subject_id"] for r in rows]
        topic_totals = dict(
            Topic.objects.filter(chapter__subject_id__in=subject_ids)
            .values("chapter__subject_id")
            .annotate(n=Count("id"))
            .values_list("chapter__subject_id", "n")
        )
        diag_counts = dict(
            Diagnost_Student.objects.filter(student=child, subject_id__in=subject_ids)
            .values("subject_id")
            .annotate(n=Count("id"))
            .values_list("subject_id", "n")
        )
        subjects = [
            {
                "id": r["topic__chapter__subject_id"],
                "name_uz": r["topic__chapter__subject__name_uz"],
                "name_ru": r["topic__chapter__subject__name_ru"],
                "class_name": r["topic__chapter__subject__classes__name"] or "",
                "percent": round(r["avg"] or 0),
                "completed_topics": r["done"],
                "total_topics": topic_totals.get(r["topic__chapter__subject_id"], 0),
                "tests": r["tests"],
                "diagnostics": diag_counts.get(r["topic__chapter__subject_id"], 0),
            }
            for r in rows
        ]
        available_subjects = Subject.objects.filter(classes=class_obj).count() if class_obj else 0

        # ---- Boblar bo'yicha natija (radar) ----
        chapters = [
            {"name_uz": r["topic__chapter__name_uz"], "name_ru": r["topic__chapter__name_ru"], "percent": round(r["avg"] or 0)}
            for r in TopicProgress.objects.filter(user=child)
            .values("topic__chapter_id", "topic__chapter__name_uz", "topic__chapter__name_ru")
            .annotate(avg=Avg("score"), n=Count("id"))
            .order_by("-n")[:6]
        ]

        # ---- Statistika kartalari ----
        dates = activity_dates(child, days=60)
        active_now = sum(1 for d in dates if d > today - timedelta(days=30))
        active_prev = sum(1 for d in dates if today - timedelta(days=60) < d <= today - timedelta(days=30))
        progress = TopicProgress.objects.filter(user=child)
        tests_now = progress.filter(completed_at__gte=month_ago).count()
        tests_prev = progress.filter(completed_at__gte=two_months_ago, completed_at__lt=month_ago).count()
        avg_all = progress.aggregate(a=Avg("score"))["a"]
        avg_now = progress.filter(completed_at__gte=month_ago).aggregate(a=Avg("score"))["a"]
        avg_prev = progress.filter(completed_at__gte=two_months_ago, completed_at__lt=month_ago).aggregate(a=Avg("score"))["a"]
        stats = {
            "activity": {"percent": _percent(active_now, 30), "delta": _percent(active_now, 30) - _percent(active_prev, 30)},
            "subjects": {"studied": len(subjects), "total": max(available_subjects, len(subjects))},
            "study_time_30": _duration_seconds(child, since=month_ago),
            "tests": {"count": progress.count(), "delta": tests_now - tests_prev},
            "correct": {
                "percent": round(avg_all or 0),
                "delta": round(avg_now - avg_prev) if avg_now is not None and avg_prev is not None else None,
            },
        }

        # ---- 30 kunlik faollik (yechilgan misollar) ----
        daily = dict(
            StudentScoreLog.objects.filter(student_score__student=child, awarded_at__gte=now - timedelta(days=30))
            .annotate(day=TruncDate("awarded_at"))
            .values("day")
            .annotate(n=Count("id"))
            .values_list("day", "n")
        )
        activity_days = [
            {"date": (today - timedelta(days=o)).isoformat(), "count": daily.get(today - timedelta(days=o), 0)}
            for o in range(29, -1, -1)
        ]

        # ---- So'nggi faoliyatlar ----
        recent = [
            _recent_item("login", h.login_time)
            for h in StudentLoginHistory.objects.filter(student=child).order_by("-login_time")[:RECENT_LIMIT]
        ]
        for tp in (
            TopicProgress.objects.filter(user=child, completed_at__isnull=False)
            .select_related("topic__chapter__subject")
            .order_by("-completed_at")[:RECENT_LIMIT]
        ):
            subject = tp.topic.chapter.subject if tp.topic and tp.topic.chapter else None
            recent.append(_recent_item(
                "topic_test", tp.completed_at, tp.topic.name_uz, tp.topic.name_ru,
                subject.name_uz if subject else "", subject.name_ru if subject else "", round(tp.score),
            ))
        for diag in (
            Diagnost_Student.objects.filter(student=child, create_date__isnull=False)
            .select_related("subject")
            .order_by("-create_date")[:RECENT_LIMIT]
        ):
            recent.append(_recent_item(
                "diagnostic", diag.create_date,
                diag.subject.name_uz if diag.subject else "", diag.subject.name_ru if diag.subject else "",
                value=_diag_score(diag),
            ))
        for award in StudentAchievement.objects.filter(student=child).select_related("achievement").order_by("-awarded_at")[:RECENT_LIMIT]:
            recent.append(_recent_item(
                "achievement", award.awarded_at, award.achievement.title_uz, award.achievement.title_ru,
                award.achievement.description_uz, award.achievement.description_ru,
            ))
        recent.sort(key=lambda x: x["at"], reverse=True)

        # ---- Qurilmalar ----
        devices = [
            serialize_device(d)
            for d in UserDevice.objects.filter(user=child.user).order_by("-is_active", "-last_used_at")[:6]
        ]

        return Response({
            "profile": profile,
            "subscription": subscription,
            "payments": payment_info,
            "stats": stats,
            "subjects": subjects,
            "chapters": chapters,
            "activity_days": activity_days,
            "recent": recent[:RECENT_LIMIT],
            "devices": devices,
            "achievements": student_achievements(child, request)[0],
        })


# ---------------------------------------------------------------------------
# Farzand to'lovlari: GET /api/v1/func_student/parent/children/<id>/payments/?months=6
# ---------------------------------------------------------------------------

GATEWAY_LABELS = {"multicard": "Multicard", "payme": "Payme", "click": "Click", "uzum": "Uzum"}


def _gateway_label(value):
    if not value:
        return ""
    return GATEWAY_LABELS.get(str(value).lower(), str(value).capitalize())


def _month_starts(count):
    """Oxirgi `count` oyning birinchi kunlari (eskidan yangiga)."""
    today = timezone.localdate()
    year, month = today.year, today.month
    starts = []
    for _ in range(count):
        starts.append((year, month))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(starts))


class ParentChildPaymentsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        from django_app.app_payments.models import Payment
        from django_app.app_user.models import Subject

        parent = getattr(request.user, "parent_profile", None)
        relation = None
        if parent is not None:
            relation = (
                ParentStudentRelation.objects.filter(parent=parent, student_id=student_id, is_confirmed=True)
                .select_related("student__class_name__classes")
                .first()
            )
        if relation is None:
            return Response({"detail": "Farzand topilmadi."}, status=status.HTTP_404_NOT_FOUND)
        child = relation.student

        try:
            months_param = int(request.query_params.get("months", 6))
        except (TypeError, ValueError):
            months_param = 6
        months_param = 12 if months_param >= 12 else 6

        now = timezone.now()
        payments = list(
            Payment.objects.filter(student=child)
            .exclude(status="failed")
            .select_related("coupon")
            .order_by("-payment_date", "-created_at")
        )
        success = [p for p in payments if p.status == "success"]
        last = success[0] if success else None

        def paid_at(payment):
            return payment.payment_date or payment.created_at

        # ---- Joriy tarif ----
        try:
            sub = child.subscription
        except Exception:  # noqa: BLE001 — obuna yo'q
            sub = None
        class_obj = getattr(child.class_name, "classes", None) if child.class_name else None
        subject_names = list(
            Subject.objects.filter(classes=class_obj).order_by("order").values("name_uz", "name_ru")
        ) if class_obj else []

        current = None
        if sub is not None:
            months = last.subscription_months if last else None
            period_start = sub.start_date
            if months and sub.end_date:
                period_start = max(sub.start_date or sub.end_date, sub.end_date - timedelta(days=30 * months))
            total_days = max(1, (sub.end_date - period_start).days) if period_start and sub.end_date else 0
            current = {
                "is_active": bool(sub.end_date and sub.end_date >= now),
                "months": months,
                "start_date": period_start.isoformat() if period_start else None,
                "end_date": sub.end_date.isoformat() if sub.end_date else None,
                "next_payment_date": (sub.next_payment_date or sub.end_date).isoformat() if (sub.next_payment_date or sub.end_date) else None,
                "days_left": max(0, (sub.end_date - now).days) if sub.end_date else 0,
                "total_days": total_days,
                "subjects": subject_names,
            }

        total_paid = float(sum(p.amount for p in success))
        total_months = sum(p.subscription_months or 1 for p in success)

        # ---- Oylik statistika (muvaffaqiyatli to'lovlar) ----
        sums = defaultdict(float)
        for payment in success:
            moment = timezone.localtime(paid_at(payment)) if timezone.is_aware(paid_at(payment)) else paid_at(payment)
            sums[(moment.year, moment.month)] += float(payment.amount)
        monthly = [{"year": y, "month": m, "amount": sums.get((y, m), 0)} for y, m in _month_starts(months_param)]

        history = [
            {
                "id": payment.id,
                "number": len(payments) - index,
                "date": paid_at(payment).isoformat(),
                "amount": float(payment.amount),
                "original_amount": float(payment.original_amount) if payment.original_amount else None,
                "discount_percent": payment.discount_percent,
                "months": payment.subscription_months,
                "gateway": _gateway_label(payment.payment_gateway),
                "status": payment.status,
                "receipt_url": payment.receipt_url or "",
                # Kvitansiya ("Ko'rish") oynasi uchun
                "student_name": child.full_name,
                "store_id": payment.store_id or "",
                "invoice_uuid": payment.invoice_uuid or "",
                "uuid": payment.uuid or "",
                "billing_id": payment.billing_id or "",
                "sign": payment.sign or "",
                "transaction_id": payment.transaction_id or "",
                "coupon_code": payment.coupon.code if payment.coupon else "",
                "coupon_type": payment.get_coupon_type_display() if payment.coupon_type else "",
                "discount_amount": (
                    float(payment.original_amount - payment.amount)
                    if payment.original_amount and payment.original_amount > payment.amount else 0
                ),
            }
            for index, payment in enumerate(payments)
        ]

        return Response({
            "current": current,
            "summary": {
                "total_paid": total_paid,
                "success_count": len(success),
                "last_amount": float(last.amount) if last else 0,
                "last_date": paid_at(last).isoformat() if last else None,
                "last_gateway": _gateway_label(last.payment_gateway) if last else "",
                # Oylik ekvivalent: jami to'langan / jami sotib olingan oylar
                "monthly_equivalent": round(total_paid / total_months) if total_months else 0,
            },
            "monthly": monthly,
            "history": history,
        })
