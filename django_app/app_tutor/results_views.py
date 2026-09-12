"""
O'qituvchi (tutor) o'z o'quvchilarining natijalarini ko'rishi uchun API'lar.

Natijalar app_student.TopicProgress (mavzu bo'yicha ball), StudentScore (umumiy ball/coin)
va Diagnost_Student (diagnostika) ma'lumotlaridan hisoblanadi.
"""

from datetime import timedelta

from django.db.models import Avg, Count, Max, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_student.models import Diagnost_Student, StudentScore, TopicProgress
from django_app.app_teacher.models import Topic

from .helpers import IsTutor, get_tutor, get_tutor_students
from .models import TutorCouponTransaction, TutorGroup, TutorReferralTransaction

# SubjectListWithMasteryAPIView bilan bir xil chegara
MASTERY_THRESHOLD = 80
DEFAULT_PERIOD_DAYS = 30


def _round(value, digits=1):
    return round(float(value), digits) if value is not None else 0.0


def _percent(part, total, digits=1):
    if not total:
        return 0.0
    return round((part / total) * 100, digits)


def _summaries_for_students(student_ids):
    """Bir nechta o'quvchi uchun natija xulosasini bitta so'rovda hisoblaydi."""
    rows = (
        TopicProgress.objects.filter(user_id__in=student_ids)
        .values('user_id')
        .annotate(
            attempted=Count('id'),
            mastered=Count('id', filter=Q(score__gte=MASTERY_THRESHOLD)),
            average=Avg('score'),
            last_activity=Max('completed_at'),
        )
    )

    summaries = {}
    for row in rows:
        attempted = row['attempted'] or 0
        mastered = row['mastered'] or 0
        summaries[row['user_id']] = {
            "attempted_topics": attempted,
            "mastered_topics": mastered,
            "average_score": _round(row['average']),
            "mastery_percent": _percent(mastered, attempted),
            "last_activity": row['last_activity'].strftime("%d/%m/%Y %H:%M") if row['last_activity'] else None,
        }

    empty = {
        "attempted_topics": 0,
        "mastered_topics": 0,
        "average_score": 0.0,
        "mastery_percent": 0.0,
        "last_activity": None,
    }
    return {student_id: summaries.get(student_id, dict(empty)) for student_id in student_ids}


def _student_row(student, summary, score_map, group_map):
    score = score_map.get(student.id)
    group = group_map.get(student.id)
    return {
        "id": student.id,
        "full_name": student.full_name,
        "identification": student.identification,
        "phone": student.user.phone if student.user_id else None,
        "class_uz": (
            f"{student.class_name.classes.name}-sinf {student.class_name.name_uz}"
            if student.class_name and student.class_name.classes else
            (student.class_name.name_uz if student.class_name else None)
        ),
        "group_id": group['id'] if group else None,
        "group_name": group['name'] if group else None,
        "score": score['score'] if score else 0,
        "coin": score['coin'] if score else 0,
        **summary,
    }


def _score_map(student_ids):
    return {
        row['student_id']: row
        for row in StudentScore.objects.filter(student_id__in=student_ids).values(
            'student_id', 'score', 'coin', 'som'
        )
    }


def _group_map(tutor, student_ids):
    """student_id -> {id, name} (tutorning qaysi guruhida ekanligi)."""
    mapping = {}
    groups = TutorGroup.objects.filter(tutor=tutor).prefetch_related('students')
    for group in groups:
        for student in group.students.all():
            if student.id in student_ids:
                mapping[student.id] = {"id": group.id, "name": group.name}
    return mapping


def _build_student_rows(tutor, students):
    students = list(students)
    student_ids = [student.id for student in students]
    summaries = _summaries_for_students(student_ids)
    score_map = _score_map(student_ids)
    group_map = _group_map(tutor, set(student_ids))
    return [
        _student_row(student, summaries[student.id], score_map, group_map)
        for student in students
    ]


class TutorStudentsResultsAPIView(APIView):
    """
    GET /api/v1/tutor/tutor/results/students/ - barcha o'quvchilarning natijalari ro'yxati.

    Query params:
      ?group_id=<id>  - faqat shu guruh o'quvchilari
      ?search=<matn>
      ?ordering=average_score|-average_score|full_name|-attempted_topics ...
    """
    permission_classes = [IsTutor]

    def get(self, request):
        tutor = get_tutor(request)
        students = get_tutor_students(tutor)

        search = request.GET.get('search')
        if search:
            students = students.filter(
                Q(full_name__icontains=search) | Q(identification__icontains=search)
            )

        group_id = request.GET.get('group_id')
        if group_id:
            students = students.filter(tutor_groups__id=group_id, tutor_groups__tutor=tutor)

        rows = _build_student_rows(tutor, students.distinct())

        ordering = request.GET.get('ordering')
        if ordering:
            reverse = ordering.startswith('-')
            key = ordering.lstrip('-')
            if rows and key in rows[0]:
                rows.sort(key=lambda row: (row[key] is None, row[key]), reverse=reverse)

        return Response({"count": len(rows), "results": rows}, status=status.HTTP_200_OK)


class TutorStudentResultDetailAPIView(APIView):
    """
    GET /api/v1/tutor/tutor/results/students/<student_id>/ - bitta o'quvchining
    to'liq natijasi: umumiy xulosa, fanlar kesimi, oxirgi ishlangan mavzular, diagnostika.
    """
    permission_classes = [IsTutor]

    def get(self, request, student_id):
        tutor = get_tutor(request)
        student = get_tutor_students(tutor).filter(id=student_id).first()
        if student is None:
            return Response(
                {"detail": "Bu o'quvchi sizning o'quvchingiz emas"},
                status=status.HTTP_404_NOT_FOUND
            )

        progresses = list(
            TopicProgress.objects.filter(user=student)
            .select_related('topic', 'topic__chapter', 'topic__chapter__subject',
                            'topic__chapter__subject__classes')
        )

        attempted = len(progresses)
        mastered = sum(1 for p in progresses if p.score >= MASTERY_THRESHOLD)
        average = _round(sum(p.score for p in progresses) / attempted) if attempted else 0.0

        # === Fanlar kesimi ===
        by_subject = {}
        for progress in progresses:
            chapter = progress.topic.chapter if progress.topic else None
            subject = chapter.subject if chapter else None
            if subject is None:
                continue
            bucket = by_subject.setdefault(subject.id, {"subject": subject, "items": []})
            bucket["items"].append(progress)

        subject_total_topics = {
            row['chapter__subject']: row['total']
            for row in Topic.objects.filter(chapter__subject_id__in=by_subject.keys())
            .values('chapter__subject')
            .annotate(total=Count('id'))
        }

        subjects = []
        for subject_id, bucket in by_subject.items():
            subject = bucket["subject"]
            items = bucket["items"]
            subject_attempted = len(items)
            subject_mastered = sum(1 for p in items if p.score >= MASTERY_THRESHOLD)
            total_topics = subject_total_topics.get(subject_id, 0)
            subjects.append({
                "id": subject.id,
                "name_uz": subject.name_uz,
                "name_ru": subject.name_ru,
                "class_uz": (
                    f"{subject.classes.name}-sinf {subject.name_uz}" if subject.classes else subject.name_uz
                ),
                "class_ru": (
                    f"{subject.classes.name}-класс {subject.name_ru}" if subject.classes else subject.name_ru
                ),
                "total_topics": total_topics,
                "attempted_topics": subject_attempted,
                "mastered_topics": subject_mastered,
                "average_score": _round(sum(p.score for p in items) / subject_attempted),
                "progress_percent": _percent(subject_attempted, total_topics),
                "mastery_percent": _percent(subject_mastered, total_topics),
            })
        subjects.sort(key=lambda item: item["average_score"], reverse=True)

        # === Oxirgi ishlangan mavzular ===
        recent = sorted(
            [p for p in progresses if p.completed_at],
            key=lambda p: p.completed_at,
            reverse=True
        )[:15]
        recent_topics = [{
            "topic_id": p.topic_id,
            "topic_name_uz": p.topic.name_uz if p.topic else None,
            "topic_name_ru": p.topic.name_ru if p.topic else None,
            "chapter_name_uz": p.topic.chapter.name_uz if p.topic and p.topic.chapter else None,
            "subject_name_uz": (
                p.topic.chapter.subject.name_uz
                if p.topic and p.topic.chapter and p.topic.chapter.subject else None
            ),
            "score": _round(p.score),
            "is_mastered": p.score >= MASTERY_THRESHOLD,
            "completed_at": p.completed_at.strftime("%d/%m/%Y %H:%M"),
        } for p in recent]

        # === Diagnostika ===
        diagnostics = [{
            "id": item.id,
            "subject_uz": item.subject.name_uz if item.subject else None,
            "subject_ru": item.subject.name_ru if item.subject else None,
            "level": item.level,
            "created_at": item.create_date.strftime("%d/%m/%Y %H:%M") if item.create_date else None,
        } for item in Diagnost_Student.objects.filter(student=student).select_related('subject')]

        # === Obuna va ball ===
        score = StudentScore.objects.filter(student=student).first()
        subscription = getattr(student, 'subscription', None)
        subscription_data = None
        if subscription:
            remaining = (subscription.end_date.date() - timezone.now().date()).days
            subscription_data = {
                "is_paid": subscription.is_paid,
                "is_active": subscription.start_date <= timezone.now() <= subscription.end_date,
                "end_date": subscription.end_date.strftime("%d/%m/%Y"),
                "remaining_days": remaining if remaining > 0 else 0,
            }

        group = TutorGroup.objects.filter(tutor=tutor, students=student).first()

        return Response({
            "student": {
                "id": student.id,
                "full_name": student.full_name,
                "identification": student.identification,
                "phone": student.user.phone if student.user_id else None,
                "email": student.user.email if student.user_id else None,
                "region": student.region,
                "districts": student.districts,
                "class_uz": (
                    f"{student.class_name.classes.name}-sinf {student.class_name.name_uz}"
                    if student.class_name and student.class_name.classes else None
                ),
                "registered_at": student.student_date.strftime("%d/%m/%Y") if student.student_date else None,
                "group_id": group.id if group else None,
                "group_name": group.name if group else None,
            },
            "subscription": subscription_data,
            "score": {
                "score": score.score if score else 0,
                "coin": score.coin if score else 0,
                "som": score.som if score else 0,
            },
            "summary": {
                "attempted_topics": attempted,
                "mastered_topics": mastered,
                "average_score": average,
                "mastery_percent": _percent(mastered, attempted),
            },
            "subjects": subjects,
            "recent_topics": recent_topics,
            "diagnostics": diagnostics,
        }, status=status.HTTP_200_OK)


class TutorGroupResultsAPIView(APIView):
    """
    GET /api/v1/tutor/tutor/groups/<pk>/results/ - guruh natijalari:
    guruh o'rtacha ko'rsatkichi + har bir o'quvchi kesimi.
    """
    permission_classes = [IsTutor]

    def get(self, request, pk):
        tutor = get_tutor(request)
        group = get_object_or_404(TutorGroup, pk=pk, tutor=tutor)

        students = group.students.select_related('user', 'class_name', 'class_name__classes')
        rows = _build_student_rows(tutor, students)

        attempted_total = sum(row["attempted_topics"] for row in rows)
        mastered_total = sum(row["mastered_topics"] for row in rows)
        scored_rows = [row for row in rows if row["attempted_topics"]]
        group_average = (
            _round(sum(row["average_score"] for row in scored_rows) / len(scored_rows))
            if scored_rows else 0.0
        )

        return Response({
            "group": {
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "is_active": group.is_active,
                "student_count": len(rows),
                "created_at": group.created_at.strftime("%d/%m/%Y %H:%M"),
            },
            "summary": {
                "student_count": len(rows),
                "active_students": len(scored_rows),
                "attempted_topics": attempted_total,
                "mastered_topics": mastered_total,
                "average_score": group_average,
                "mastery_percent": _percent(mastered_total, attempted_total),
            },
            "students": rows,
        }, status=status.HTTP_200_OK)


class TutorResultsOverviewAPIView(APIView):
    """
    GET /api/v1/tutor/tutor/results/overview/?period=30 - tutor paneli uchun
    umumiy statistika (o'quvchilar, guruhlar, o'tilgan mavzular, o'rtacha natija).
    """
    permission_classes = [IsTutor]

    def get(self, request):
        tutor = get_tutor(request)

        try:
            period_days = int(request.GET.get('period', DEFAULT_PERIOD_DAYS))
        except (TypeError, ValueError):
            period_days = DEFAULT_PERIOD_DAYS
        period_days = max(1, min(period_days, 365))

        now = timezone.now()
        period_start = now - timedelta(days=period_days)
        prev_start = period_start - timedelta(days=period_days)

        students = get_tutor_students(tutor)
        student_ids = list(students.values_list('id', flat=True))

        groups = TutorGroup.objects.filter(tutor=tutor)
        grouped_ids = {
            sid for sid in groups.values_list('students__id', flat=True) if sid
        }

        new_students = (
            TutorReferralTransaction.objects.filter(tutor=tutor, used_at__gte=period_start)
            .values_list('student_id', flat=True)
        )
        new_coupon_students = (
            TutorCouponTransaction.objects.filter(tutor=tutor, used_at__gte=period_start)
            .values_list('student_id', flat=True)
        )

        progress_qs = TopicProgress.objects.filter(user_id__in=student_ids)
        period_qs = progress_qs.filter(completed_at__gte=period_start)
        prev_qs = progress_qs.filter(completed_at__gte=prev_start, completed_at__lt=period_start)

        period_stats = period_qs.aggregate(completed=Count('id'), average=Avg('score'))
        prev_stats = prev_qs.aggregate(completed=Count('id'), average=Avg('score'))

        active_student_count = period_qs.values('user_id').distinct().count()
        overall_average = _round(progress_qs.aggregate(average=Avg('score'))['average'])

        period_average = _round(period_stats['average'])
        prev_average = _round(prev_stats['average'])

        return Response({
            "period_days": period_days,
            "students": {
                "total": len(student_ids),
                "new_in_period": len(set(new_students) | set(new_coupon_students)),
                "in_groups": len(grouped_ids),
                "without_group": len(set(student_ids) - grouped_ids),
                "active_in_period": active_student_count,
            },
            "groups": {
                "total": groups.count(),
                "new_in_period": groups.filter(created_at__gte=period_start).count(),
            },
            "topics": {
                "completed_in_period": period_stats['completed'] or 0,
                "completed_prev_period": prev_stats['completed'] or 0,
                "growth": (period_stats['completed'] or 0) - (prev_stats['completed'] or 0),
            },
            "average_result": {
                "overall_percent": overall_average,
                "period_percent": period_average,
                "prev_period_percent": prev_average,
                "growth": _round(period_average - prev_average),
            },
        }, status=status.HTTP_200_OK)


class TutorResultsChartAPIView(APIView):
    """
    GET /api/v1/tutor/tutor/results/chart/?period=30 - o'quvchilar natijalari dinamikasi.

    Har bir nuqta - shu sanagacha ishlangan barcha mavzular bo'yicha o'rtacha ball
    (kumulyativ o'rtacha). Shu sababli faoliyatsiz haftalarda chiziq nolga tushmaydi.
    """
    permission_classes = [IsTutor]

    BUCKETS = 5

    def get(self, request):
        tutor = get_tutor(request)

        try:
            period_days = int(request.GET.get('period', DEFAULT_PERIOD_DAYS))
        except (TypeError, ValueError):
            period_days = DEFAULT_PERIOD_DAYS
        period_days = max(7, min(period_days, 365))

        student_ids = list(get_tutor_students(tutor).values_list('id', flat=True))
        now = timezone.now()
        step = period_days / self.BUCKETS

        points = []
        for index in range(self.BUCKETS):
            end = now - timedelta(days=step * (self.BUCKETS - index - 1))
            average = TopicProgress.objects.filter(
                user_id__in=student_ids, completed_at__lt=end
            ).aggregate(average=Avg('score'))['average']

            points.append({
                "date": end.strftime("%Y-%m-%d"),
                "label": end.strftime("%d.%m"),
                "value": _round(average),
            })

        return Response({
            "period_days": period_days,
            "labels": [point["label"] for point in points],
            "values": [point["value"] for point in points],
            "points": points,
        }, status=status.HTTP_200_OK)
