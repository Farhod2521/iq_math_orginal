from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_student.paginations import StandardResultsSetPagination
from django_app.app_student.privacy import public_name
from django_app.app_user.models import Class, Student, Subject

from . import services
from .models import LigaAttempt, LigaParticipant, LigaPointLog, LigaQuestion, LigaSeason, LigaTest, LigaWinner
from .serializers import (
    AdminQuestionSerializer, AdminSeasonSerializer, AdminTestSerializer, AdminWinnerSerializer,
    AnswerInputSerializer, BulkTestSerializer, PublicSeasonSerializer, StudentQuestionSerializer,
)

TOP_SIZE = 10


class IsLigaAdmin(BasePermission):
    """Ligani mentor (teacher), admin va superadmin boshqaradi."""

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
            and getattr(request.user, 'role', None) in ('teacher', 'admin', 'superadmin')
        )


def _get_student(request):
    if not request.user.is_authenticated:
        return None
    return Student.objects.select_related('class_name', 'class_name__classes').filter(user=request.user).first()


def _current_season():
    """Ochiq mavsum, u bo'lmasa oxirgi yopilgani (g'oliblarini ko'rsatish uchun)."""
    published = LigaSeason.objects.filter(is_published=True)
    return (
        published.filter(closed_at__isnull=True).order_by('number').first()
        or published.order_by('-number').first()
    )


def _viewer(student):
    """Sahifadagi suv belgisi uchun: skrinshot tarqalsa, kimniki ekani bilinadi."""
    return f"{student.full_name} · {student.identification}"


def _winner_row(winner):
    return {
        'place': winner.place,
        'grade': winner.grade.name,
        'full_name': public_name(winner.student.full_name),
        'points': winner.points,
        'prize_uz': winner.prize_uz,
        'prize_ru': winner.prize_ru,
        'is_disqualified': winner.is_disqualified,
    }


def _standing_row(participant):
    return {
        'rank': participant.rank,
        'full_name': public_name(participant.student.full_name),
        'points': participant.points,
    }


def _subject_stats(attempt):
    rows = (
        attempt.answers.values('question__subject__name')
        .annotate(answered=Count('id'), correct=Count('id', filter=Q(is_correct=True)))
        .order_by('question__subject__name')
    )
    return [
        {'subject': row['question__subject__name'], 'answered': row['answered'], 'correct': row['correct']}
        for row in rows
    ]


def _attempt_summary(attempt):
    data = {
        'id': attempt.id,
        'test': attempt.test_id,
        'status': attempt.status,
        'started_at': attempt.started_at,
        'deadline_at': attempt.deadline_at,
        'finished_at': attempt.finished_at,
        'duration_seconds': attempt.duration_seconds,
        'total_questions': attempt.total_questions,
    }
    if attempt.status != LigaAttempt.STATUS_IN_PROGRESS:
        data.update({
            'answered_count': attempt.answered_count,
            'correct_count': attempt.correct_count,
            'wrong_count': attempt.wrong_count,
            'score': attempt.score,
            'max_score': attempt.max_score,
            'by_subject': _subject_stats(attempt),
        })
    return data


def _attempt_payload(attempt, request):
    data = _attempt_summary(attempt)
    if attempt.status != LigaAttempt.STATUS_IN_PROGRESS:
        return data

    questions = LigaQuestion.objects.filter(id__in=attempt.question_order).select_related('subject').prefetch_related('choices')
    by_id = {question.id: question for question in questions}
    ordered = [by_id[pk] for pk in attempt.question_order if pk in by_id]
    data.update({
        'viewer': _viewer(attempt.student),
        'week_number': attempt.test.week_number,
        'remaining_seconds': max(0, int((attempt.deadline_at - timezone.now()).total_seconds())),
        'questions': StudentQuestionSerializer(ordered, many=True, context={'request': request}).data,
        'answers': [
            {'question': answer.question_id, 'choice': answer.selected_choice_id, 'text_answer': answer.text_answer}
            for answer in attempt.answers.all()
        ],
    })
    return data


def _test_row(test, attempt):
    return {
        'id': test.id,
        'week_number': test.week_number,
        'start_at': test.start_at,
        'end_at': test.end_at,
        'duration_minutes': test.duration_minutes,
        'question_count': test.question_count,
        'status': test.status,
        'attempt': _attempt_summary(attempt) if attempt else None,
    }


# ---------- O'quvchi ----------

class CurrentSeasonAPIView(APIView):
    """Liga sahifasi: mavsum, o'quvchi sinfining testlari va shu sinf reytingi."""
    permission_classes = [AllowAny]

    def get(self, request):
        season = _current_season()
        if not season:
            return Response({'season': None})

        data = {'season': PublicSeasonSerializer(season).data}
        student = _get_student(request)
        if not student:
            return Response(data)

        participant = LigaParticipant.objects.filter(season=season, student=student).first()
        # Qo'shilgach sinf o'zgartirilsa ham ligada ro'yxatdan o'tgan sinfi qoladi
        grade_id = participant.grade_id if participant else services.student_grade_id(student)

        tests = list(season.tests.filter(is_published=True, grade_id=grade_id).select_related('season'))
        attempts = {
            attempt.test_id: services.finalize_if_expired(attempt)
            for attempt in LigaAttempt.objects.filter(test__in=tests, student=student).select_related('test')
        }
        ranked = services.standings(season, grade_id) if grade_id and not season.is_closed else []
        me = next((item for item in ranked if item.student_id == student.id), None)
        winners = season.winners.filter(grade_id=grade_id).select_related('student', 'grade').order_by('place')

        data.update({
            'grade': Class.objects.filter(pk=grade_id).values_list('name', flat=True).first(),
            'subscription_active': services.is_subscription_active(student),
            'joined': bool(participant),
            'points': participant.points if participant else 0,
            'rank': me.rank if me else None,
            'participants_count': len(ranked),
            'tests': [_test_row(test, attempts.get(test.id)) for test in tests],
            'top': [_standing_row(item) for item in ranked[:TOP_SIZE]],
            'winners': [_winner_row(winner) for winner in winners],
            'viewer': _viewer(student),
        })
        return Response(data)


class JoinSeasonAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, season_id):
        student = _get_student(request)
        if not student:
            return Response({'message': "O'quvchi topilmadi"}, status=404)
        season = get_object_or_404(LigaSeason, id=season_id, is_published=True)
        try:
            services.join_season(season, student)
        except services.LigaError as exc:
            return Response({'message': str(exc)}, status=400)
        # Qo'shilgan kuni ham kirgani uchun ball beriladi
        services.award_daily_login(student.id)
        return Response({'joined': True}, status=status.HTTP_201_CREATED)


class WinnersHistoryAPIView(APIView):
    """Yopilgan mavsumlar g'oliblari — ballar nolga tushsa ham saqlanib qoladi."""
    permission_classes = [AllowAny]

    def get(self, request):
        seasons = LigaSeason.objects.filter(is_published=True, closed_at__isnull=False).prefetch_related(
            'winners__student', 'winners__grade',
        )
        return Response([
            {
                'id': season.id,
                'number': season.number,
                'closed_at': season.closed_at,
                'winners': [_winner_row(winner) for winner in season.winners.all()],
            }
            for season in seasons
        ])


class StudentAttemptView(APIView):
    permission_classes = [IsAuthenticated]

    def get_attempt(self, request, attempt_id):
        student = _get_student(request)
        return get_object_or_404(LigaAttempt.objects.select_related('test', 'student'), id=attempt_id, student=student)


class StartTestAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, test_id):
        student = _get_student(request)
        if not student:
            return Response({'message': "O'quvchi topilmadi"}, status=404)
        test = get_object_or_404(
            LigaTest.objects.select_related('season'), id=test_id, is_published=True, season__is_published=True,
        )
        try:
            attempt = services.start_attempt(test, student)
        except services.LigaError as exc:
            return Response({'message': str(exc)}, status=400)
        return Response(_attempt_payload(attempt, request), status=status.HTTP_201_CREATED)


class AttemptDetailAPIView(StudentAttemptView):
    def get(self, request, attempt_id):
        attempt = services.finalize_if_expired(self.get_attempt(request, attempt_id))
        return Response(_attempt_payload(attempt, request))


class AttemptAnswerAPIView(StudentAttemptView):
    def post(self, request, attempt_id):
        attempt = self.get_attempt(request, attempt_id)
        serializer = AnswerInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            services.save_answer(attempt.id, data['question'], data.get('choice'), data.get('text_answer'))
        except services.LigaError as exc:
            return Response({'message': str(exc)}, status=400)
        return Response({'saved': True})


class AttemptFinishAPIView(StudentAttemptView):
    def post(self, request, attempt_id):
        attempt = services.finish_attempt(self.get_attempt(request, attempt_id).id)
        return Response(_attempt_summary(attempt))


# ---------- Mentor / admin ----------

def _xlsx(filename, sheet_title, header, rows):
    book = Workbook()
    sheet = book.active
    sheet.title = sheet_title
    sheet.append(header)
    for row in rows:
        sheet.append(row)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
    book.save(response)
    return response


class ProtectedDestroyMixin:
    def has_results(self, instance):
        raise NotImplementedError

    def destroy(self, request, *args, **kwargs):
        if self.has_results(self.get_object()):
            return Response({'message': "Natijalari bor yozuvni o'chirib bo'lmaydi"}, status=400)
        return super().destroy(request, *args, **kwargs)


class AdminMetaAPIView(APIView):
    """Formalar uchun: sinflar va ularning fanlari."""
    permission_classes = [IsLigaAdmin]

    def get(self, request):
        return Response({
            'grades': list(Class.objects.values('id', 'name')),
            'subjects': [
                {'id': subject.id, 'name': subject.name, 'grade': subject.classes_id}
                for subject in Subject.objects.filter(active=True, classes__isnull=False)
            ],
        })


class AdminSeasonViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = LigaSeason.objects.all()
    serializer_class = AdminSeasonSerializer
    permission_classes = [IsLigaAdmin]

    def has_results(self, instance):
        return instance.participants.exists() or LigaAttempt.objects.filter(test__season=instance).exists()

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Mavsumni qo'lda yopish: g'oliblar saqlanadi, ballar nolga tushadi."""
        season = services.close_season(self.get_object().id)
        return Response(self.get_serializer(season).data)

    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        season = self.get_object()
        finished = LigaAttempt.objects.filter(test__season=season).exclude(status=LigaAttempt.STATUS_IN_PROGRESS)
        tests = season.tests.select_related('grade')
        participants = season.participants

        average = finished.aggregate(score=Avg('score'), max_score=Avg('max_score'), seconds=Avg('duration_seconds'))
        by_grade_participants = {
            row['grade']: row for row in participants.values('grade').annotate(count=Count('id'), points=Sum('points'))
        }
        by_grade_attempts = {
            row['test__grade']: row
            for row in finished.values('test__grade').annotate(count=Count('id'), score=Avg('score'), seconds=Avg('duration_seconds'))
        }
        by_week = list(
            finished.values('test__week_number').annotate(attempts=Count('id'), score=Avg('score'))
            .order_by('test__week_number')
        )
        by_source = {
            row['source']: row['total']
            for row in LigaPointLog.objects.filter(participant__season=season).values('source').annotate(total=Sum('points'))
        }

        grades = []
        for grade in Class.objects.all():
            joined = by_grade_participants.get(grade.id, {})
            taken = by_grade_attempts.get(grade.id, {})
            leader = services.standings(season, grade.id)[:1] if joined else []
            grades.append({
                'grade': grade.name,
                'grade_id': grade.id,
                'participants': joined.get('count', 0),
                'points': joined.get('points') or 0,
                'attempts': taken.get('count', 0),
                'avg_score': round(taken.get('score') or 0, 1),
                'avg_seconds': round(taken.get('seconds') or 0),
                'leader': leader[0].student.full_name if leader else None,
                'leader_points': leader[0].points if leader else 0,
            })

        return Response({
            'cards': {
                'participants': participants.count(),
                'tests_total': tests.count(),
                'tests_finished': tests.filter(end_at__lte=timezone.now()).count(),
                'attempts': finished.count(),
                'in_progress': LigaAttempt.objects.filter(test__season=season, status=LigaAttempt.STATUS_IN_PROGRESS).count(),
                'avg_score': round(average['score'] or 0, 1),
                'avg_max_score': round(average['max_score'] or 0, 1),
                'avg_seconds': round(average['seconds'] or 0),
            },
            'grades': grades,
            'weeks': [
                {'week': row['test__week_number'], 'attempts': row['attempts'], 'avg_score': round(row['score'] or 0, 1)}
                for row in by_week
            ],
            'points_by_source': {source: by_source.get(source, 0) for source, _ in LigaPointLog.SOURCES},
        })

    @action(detail=True, methods=['get'])
    def standings(self, request, pk=None):
        """Sinf reytingi jadvali: ?grade=, ?search=, ?export=xlsx"""
        season = self.get_object()
        grade_id = request.query_params.get('grade')
        grade_ids = [grade_id] if grade_id else list(season.participants.order_by('grade_id').values_list('grade_id', flat=True).distinct())

        taken = {
            row['student']: row
            for row in LigaAttempt.objects.filter(test__season=season).exclude(status=LigaAttempt.STATUS_IN_PROGRESS)
            .values('student').annotate(tests=Count('id'), score=Sum('score'))
        }
        grade_names = dict(Class.objects.values_list('id', 'name'))
        rows = []
        for current in grade_ids:
            for item in services.standings(season, current):
                student = item.student
                rows.append({
                    'rank': item.rank,
                    'grade': grade_names.get(item.grade_id),
                    'student_id': student.id,
                    'full_name': student.full_name,
                    'phone': student.user.phone,
                    'region': student.region,
                    'school': student.academy_or_school_name,
                    'points': item.points,
                    'tests_taken': taken.get(student.id, {}).get('tests', 0),
                    'test_score': taken.get(student.id, {}).get('score') or 0,
                    'joined_at': item.joined_at,
                })

        search = (request.query_params.get('search') or '').strip().lower()
        if search:
            rows = [row for row in rows if search in row['full_name'].lower() or search in (row['phone'] or '')]

        if request.query_params.get('export') == 'xlsx':
            return _xlsx(
                f'liga_{season.number}_reyting', "Reyting",
                ["O'rin", "Sinf", "F.I.Sh.", "Telefon", "Viloyat", "Maktab", "Ballar", "Ishlangan testlar", "Test ballari"],
                [
                    [row['rank'], row['grade'], row['full_name'], row['phone'], row['region'], row['school'],
                     row['points'], row['tests_taken'], row['test_score']]
                    for row in rows
                ],
            )

        paginator = StandardResultsSetPagination()
        return paginator.get_paginated_response(paginator.paginate_queryset(rows, request, view=self))


class AdminTestViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    serializer_class = AdminTestSerializer
    permission_classes = [IsLigaAdmin]

    def get_queryset(self):
        queryset = LigaTest.objects.select_related('grade', 'season')
        for param in ('season', 'grade', 'week_number'):
            value = self.request.query_params.get(param)
            if value:
                field = param if param == 'week_number' else f'{param}_id'
                queryset = queryset.filter(**{field: value})
        return queryset

    def has_results(self, instance):
        return instance.attempts.exists()

    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Bitta haftaning testini tanlangan sinflar uchun birdan yaratadi (savollari keyin kiritiladi)."""
        serializer = BulkTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        grades = Class.objects.filter(id__in=data['grades'])
        try:
            with transaction.atomic():
                tests = LigaTest.objects.bulk_create([
                    LigaTest(
                        season=data['season'], grade=grade, week_number=data['week_number'],
                        start_at=data['start_at'], end_at=data['end_at'],
                        duration_minutes=data['duration_minutes'], question_count=data['question_count'],
                    )
                    for grade in grades
                ])
        except IntegrityError:
            return Response({'message': "Bu hafta testi tanlangan sinflardan birida allaqachon bor"}, status=400)
        return Response({'created': len(tests)}, status=status.HTTP_201_CREATED)

    @staticmethod
    def _participant_row(attempt):
        student = attempt.student
        return {
            'attempt_id': attempt.id,
            'rank': getattr(attempt, 'rank', None),
            'student_id': student.id,
            'full_name': student.full_name,
            'phone': student.user.phone,
            'region': student.region,
            'district': student.districts,
            'school': student.academy_or_school_name,
            'status': attempt.status,
            'started_at': attempt.started_at,
            'finished_at': attempt.finished_at,
            'duration_seconds': attempt.duration_seconds,
            'total_questions': attempt.total_questions,
            'answered_count': attempt.answered_count,
            'correct_count': attempt.correct_count,
            'wrong_count': attempt.wrong_count,
            'score': attempt.score,
            'max_score': attempt.max_score,
        }

    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Testni ishlaganlar: o'rni, vaqti va natijasi. ?search=, ?status=, ?export=xlsx"""
        test = self.get_object()
        services.finalize_expired(test)

        rows = services.ranked_attempts(test)
        rows += list(
            test.attempts.filter(status=LigaAttempt.STATUS_IN_PROGRESS)
            .select_related('student', 'student__user').order_by('started_at')
        )

        status_filter = request.query_params.get('status')
        if status_filter:
            rows = [item for item in rows if item.status == status_filter]
        search = (request.query_params.get('search') or '').strip().lower()
        if search:
            rows = [
                item for item in rows
                if search in item.student.full_name.lower() or search in (item.student.user.phone or '')
            ]

        data = [self._participant_row(item) for item in rows]
        if request.query_params.get('export') == 'xlsx':
            return self._export(test, data)

        paginator = StandardResultsSetPagination()
        return paginator.get_paginated_response(paginator.paginate_queryset(data, request, view=self))

    @staticmethod
    def _export(test, rows):
        def local(value):
            return timezone.localtime(value).strftime('%d.%m.%Y %H:%M:%S') if value else ''

        def minutes(seconds):
            return f"{seconds // 60:02d}:{seconds % 60:02d}" if seconds is not None else ''

        return _xlsx(
            f'liga_test_{test.id}', "Natijalar",
            [
                "O'rin", "F.I.Sh.", "Telefon", "Viloyat", "Tuman", "Maktab", "Holat", "Boshlagan", "Yakunlagan",
                "Ishlagan vaqti", "Savollar", "Javob berilgan", "To'g'ri", "Noto'g'ri", "Ball", "Maksimal ball",
            ],
            [
                [
                    row['rank'], row['full_name'], row['phone'], row['region'], row['district'], row['school'],
                    row['status'], local(row['started_at']), local(row['finished_at']), minutes(row['duration_seconds']),
                    row['total_questions'], row['answered_count'], row['correct_count'], row['wrong_count'],
                    row['score'], row['max_score'],
                ]
                for row in rows
            ],
        )


class AdminQuestionViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    serializer_class = AdminQuestionSerializer
    permission_classes = [IsLigaAdmin]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        queryset = LigaQuestion.objects.select_related('subject', 'test').prefetch_related('choices')
        for param in ('test', 'subject'):
            value = self.request.query_params.get(param)
            if value:
                queryset = queryset.filter(**{f'{param}_id': value})
        return queryset

    def has_results(self, instance):
        return instance.test.attempts.exists()

    @staticmethod
    def _ensure_editable(test):
        # Test boshlangach savol o'zgarsa, o'quvchilar natijasini solishtirib bo'lmay qoladi
        if test.attempts.exists():
            raise ValidationError({'message': "Test boshlangan: savollarni o'zgartirib bo'lmaydi"})

    def perform_create(self, serializer):
        self._ensure_editable(serializer.validated_data['test'])
        serializer.save()

    def perform_update(self, serializer):
        self._ensure_editable(serializer.instance.test)
        new_test = serializer.validated_data.get('test')
        if new_test:
            self._ensure_editable(new_test)
        serializer.save()


class AdminWinnerViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """G'oliblar: hujjat tekshiruvi va sovg'adan mahrum qilish (sinfni noto'g'ri ko'rsatganlar uchun)."""
    serializer_class = AdminWinnerSerializer
    permission_classes = [IsLigaAdmin]

    def get_queryset(self):
        queryset = LigaWinner.objects.select_related('season', 'grade', 'student', 'student__user')
        season = self.request.query_params.get('season')
        return queryset.filter(season_id=season) if season else queryset
