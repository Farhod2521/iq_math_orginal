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

from django.db.models import Avg, Count
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
