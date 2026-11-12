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

from django_app.app_student.models import StudentScoreLog
from django_app.app_student.paginations import StandardResultsSetPagination
from django_app.app_student.privacy import public_name
from django_app.app_user.models import Class, Student, Subject

from . import services
from .models import LigaAttempt, LigaParticipant, LigaPointLog, LigaQuestion, LigaSeason, LigaTest, LigaWinner
from .serializers import (
    AdminQuestionSerializer, AdminSeasonSerializer, AdminTestSerializer, AdminWinnerSerializer,
    AnswerInputSerializer, BulkTestSerializer, PublicSeasonSerializer, ReviewQuestionSerializer,
    StudentQuestionSerializer, WeekSerializer,
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


def _grade_options():
    """Sinflar: raqam bo'yicha tartiblangan (1, 2, ... 11), raqamsizlari oxirida."""
    def order(item):
        digits = ''.join(ch for ch in item['name'] if ch.isdigit())
        return (int(digits) if digits else 999, item['name'])
    return sorted(Class.objects.values('id', 'name'), key=order)


def _standing_row(participant):
    return {
        'rank': participant.rank,
        'full_name': public_name(participant.student.full_name),
        'points': participant.points,
    }


def _subject_stats(attempt):
    """Fanlar bo'yicha: tushgan savollar, javob berilgani va to'g'risi."""
    totals = (
        LigaQuestion.objects.filter(id__in=attempt.question_order)
        .values('subject__name').annotate(total=Count('id')).order_by('subject__name')
    )
    answers = {
        row['question__subject__name']: row
        for row in attempt.answers.values('question__subject__name')
        .annotate(answered=Count('id'), correct=Count('id', filter=Q(is_correct=True)))
    }
    return [
        {
            'subject': row['subject__name'],
            'total': row['total'],
            'answered': answers.get(row['subject__name'], {}).get('answered', 0),
            'correct': answers.get(row['subject__name'], {}).get('correct', 0),
        }
        for row in totals
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


def _ordered_questions(attempt):
    questions = LigaQuestion.objects.filter(id__in=attempt.question_order).select_related('subject').prefetch_related('choices')
    by_id = {question.id: question for question in questions}
    return [by_id[pk] for pk in attempt.question_order if pk in by_id]


def _attempt_review(attempt, request):
    """Har bir savol: o'quvchi nima belgilagani, to'g'ri javob, to'g'ri/xato/javobsiz va olingan gol."""
    answers = {answer.question_id: answer for answer in attempt.answers.select_related('selected_choice')}
    items = []
    for number, question in enumerate(_ordered_questions(attempt), start=1):
        answer = answers.get(question.id)
        answered = bool(answer and (answer.selected_choice_id or (answer.text_answer or '').strip()))
        is_correct = bool(answered and answer.is_correct)
        correct_choice = next((choice for choice in question.choices.all() if choice.is_correct), None)
        items.append({
            'number': number,
            'question': ReviewQuestionSerializer(question, context={'request': request}).data,
            'selected_choice': answer.selected_choice_id if answered else None,
            'selected_letter': answer.selected_choice.letter if answered and answer.selected_choice else None,
            'text_answer': answer.text_answer if answered else None,
            'correct_choice': correct_choice.id if correct_choice else None,
            'correct_letter': correct_choice.letter if correct_choice else None,
            'result': 'correct' if is_correct else ('wrong' if answered else 'skipped'),
            'is_correct': is_correct,
            'earned_score': question.score if is_correct else 0,
            'max_score': question.score,
        })
    return items


def _review_block(attempt, request, force=False):
    """O'quvchiga to'g'ri javoblar test oynasi yopilgandan keyin ochiladi — boshqalar hali ishlayotgan bo'lishi mumkin."""
    if attempt.status == LigaAttempt.STATUS_IN_PROGRESS:
        return {}
    available = force or timezone.now() >= attempt.test.end_at
    review = _attempt_review(attempt, request) if available else None
    return {
        'review_available': available,
        'review_available_at': attempt.test.end_at,
        'skipped_count': attempt.total_questions - attempt.answered_count,
        'review': review,
    }


def _attempt_payload(attempt, request):
    data = _attempt_summary(attempt)
    data.update({'week_number': attempt.test.week_number, 'grade_name': attempt.test.grade.name})
    if attempt.status != LigaAttempt.STATUS_IN_PROGRESS:
        data.update(_review_block(attempt, request))
        return data

    ordered = _ordered_questions(attempt)
    data.update({
        'viewer': _viewer(attempt.student),
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
            # Qo'shilish oynasi uchun: sinflar ro'yxati va profildagi sinf (oldindan belgilanadi)
            'grades': _grade_options() if not participant else [],
            'profile_grade_id': services.student_grade_id(student),
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
        # Sinf tanlanadi va qoidalarga rozilik beriladi (eski ilova versiyalari grade yubormaydi — profildagi sinf)
        grade_id = request.data.get('grade')
        if grade_id not in (None, ''):
            if str(request.data.get('accept_rules')).lower() not in ('true', '1'):
                return Response({'message': "Qoidalarga rozilik bildiring"}, status=400)
            try:
                grade_id = int(grade_id)
            except (TypeError, ValueError):
                return Response({'message': "Sinf noto'g'ri tanlangan"}, status=400)
        else:
            grade_id = None
        try:
            services.join_season(season, student, grade_id=grade_id)
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
        return Response({**_attempt_summary(attempt), **_review_block(attempt, request)})


# ---------- O'quvchi: mavsumlar tarixi va shaxsiy tarix ----------

WEEK_TOP = 3


def _season_points(season, grade_id):
    """Sinf ishtirokchilari va mavsumda to'plagan ballari, o'rni bilan.
    Yopilgan mavsumda ballar nolga tushgani uchun ball tarixidan (LigaPointLog) yig'iladi."""
    if not season.is_closed:
        return [(item.student_id, item.student.full_name, item.points, item.rank) for item in services.standings(season, grade_id)]
    rows = list(
        season.participants.filter(grade_id=grade_id)
        .annotate(total=Sum('point_logs__points'))
        .values_list('student_id', 'student__full_name', 'total', 'joined_at')
    )
    rows.sort(key=lambda row: (-(row[2] or 0), row[3]))
    return [(sid, name, total or 0, index) for index, (sid, name, total, _) in enumerate(rows, start=1)]


def _default_grade(student):
    last = LigaParticipant.objects.filter(student=student).order_by('-season__number').first()
    return last.grade_id if last else services.student_grade_id(student)


class SeasonListAPIView(APIView):
    """Mavsumlar ro'yxati (ochiq va tugaganlar) + sinf filtri uchun sinflar."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = _get_student(request)
        seasons = (
            LigaSeason.objects.filter(is_published=True)
            .annotate(tests_count=Count('tests', filter=Q(tests__is_published=True), distinct=True))
            .order_by('-number')
        )
        return Response({
            'grade_id': _default_grade(student) if student else None,
            'grades': _grade_options(),
            'seasons': [
                {
                    'id': season.id,
                    'number': season.number,
                    'is_closed': season.is_closed,
                    'closed_at': season.closed_at,
                    'weeks_count': season.weeks_count,
                    'tests_count': season.tests_count,
                }
                for season in seasons
            ],
        })


class SeasonResultsAPIView(APIView):
    """Bitta mavsum: sinf g'oliblari (ochiq mavsumda — hozirgi yetakchilar) va har hafta testining g'oliblari."""
    permission_classes = [IsAuthenticated]

    def get(self, request, season_id):
        student = _get_student(request)
        season = get_object_or_404(LigaSeason, id=season_id, is_published=True)
        try:
            grade_id = int(request.query_params.get('grade') or 0) or (_default_grade(student) if student else None)
        except ValueError:
            grade_id = None

        ranked = _season_points(season, grade_id) if grade_id else []
        mine = next((row for row in ranked if student and row[0] == student.id), None)
        if season.is_closed:
            winners = [
                _winner_row(winner)
                for winner in season.winners.filter(grade_id=grade_id).select_related('student', 'grade').order_by('place')
            ]
        else:
            winners = [
                {'place': rank, 'full_name': public_name(name), 'points': points, 'is_disqualified': False}
                for _, name, points, rank in ranked[:WEEK_TOP] if points > 0
            ]

        weeks = []
        tests = season.tests.filter(is_published=True, grade_id=grade_id).order_by('week_number')
        for test in tests:
            row = {
                'test_id': test.id,
                'week_number': test.week_number,
                'start_at': test.start_at,
                'end_at': test.end_at,
                'status': test.status,
                'participants': 0,
                'top': [],
                'my': None,
            }
            if test.status == LigaTest.STATUS_FINISHED:
                services.finalize_expired(test)
                attempts = services.ranked_attempts(test)
                row['participants'] = len(attempts)
                row['top'] = [
                    {
                        'rank': attempt.rank,
                        'full_name': public_name(attempt.student.full_name),
                        'score': attempt.score,
                        'max_score': attempt.max_score,
                        'duration_seconds': attempt.duration_seconds,
                    }
                    for attempt in attempts if attempt.rank <= WEEK_TOP
                ]
                my = next((attempt for attempt in attempts if student and attempt.student_id == student.id), None)
                if my:
                    row['my'] = {'attempt_id': my.id, 'rank': my.rank, 'score': my.score, 'max_score': my.max_score}
            weeks.append(row)

        return Response({
            'season': PublicSeasonSerializer(season).data,
            'grade_id': grade_id,
            'grade': Class.objects.filter(pk=grade_id).values_list('name', flat=True).first(),
            'participants_count': len(ranked),
            'winners': winners,
            'me': {'points': mine[2], 'rank': mine[3]} if mine else None,
            'weeks': weeks,
            'viewer': _viewer(student) if student else None,
        })


class MyHistoryAPIView(APIView):
    """O'quvchining liga tarixi: har mavsumda to'plagan ballari, o'rni, yutuqlari va testlari."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return Response({'message': "O'quvchi topilmadi"}, status=404)

        participations = list(
            LigaParticipant.objects.filter(student=student, season__is_published=True)
            .select_related('season', 'grade').order_by('-season__number')
        )
        wins = {
            win.season_id: win
            for win in LigaWinner.objects.filter(student=student).select_related('season')
        }
        attempts = list(
            LigaAttempt.objects.filter(student=student).exclude(status=LigaAttempt.STATUS_IN_PROGRESS)
            .select_related('test', 'test__season').order_by('-test__season__number', 'test__week_number')
        )
        by_source = {
            (row['participant_id'], row['source']): row['total']
            for row in LigaPointLog.objects.filter(participant__in=participations)
            .values('participant_id', 'source').annotate(total=Sum('points'))
        }

        seasons = []
        for participant in participations:
            season = participant.season
            ranked = _season_points(season, participant.grade_id)
            mine = next((row for row in ranked if row[0] == student.id), None)
            sources = {key: by_source.get((participant.id, key), 0) or 0 for key, _ in LigaPointLog.SOURCES}
            win = wins.get(season.id)
            seasons.append({
                'season_id': season.id,
                'number': season.number,
                'is_closed': season.is_closed,
                'grade': participant.grade.name,
                'joined_at': participant.joined_at,
                'points': sum(sources.values()),
                'sources': sources,
                'rank': mine[3] if mine else None,
                'participants_count': len(ranked),
                'win': {
                    'place': win.place,
                    'prize_uz': win.prize_uz,
                    'prize_ru': win.prize_ru,
                    'is_disqualified': win.is_disqualified,
                } if win else None,
                'tests': [
                    {
                        'attempt_id': attempt.id,
                        'week_number': attempt.test.week_number,
                        'finished_at': attempt.finished_at,
                        'status': attempt.status,
                        'score': attempt.score,
                        'max_score': attempt.max_score,
                        'correct_count': attempt.correct_count,
                        'total_questions': attempt.total_questions,
                        'duration_seconds': attempt.duration_seconds,
                    }
                    for attempt in attempts if attempt.test.season_id == season.id
                ],
            })

        return Response({
            'summary': {
                'total_points': sum(item['points'] for item in seasons),
                'seasons': len(seasons),
                'tests': len(attempts),
                'wins': sum(1 for win in wins.values() if not win.is_disqualified),
                'best_rank': min((item['rank'] for item in seasons if item['rank']), default=None),
            },
            'seasons': seasons,
            'viewer': _viewer(student),
        })


class MyPointsAPIView(APIView):
    """Liga ballari qayerdan kelgani (kunlik kirish, fanlar, haftalik test). ?season=&source=&page="""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = _get_student(request)
        if not student:
            return Response({'message': "O'quvchi topilmadi"}, status=404)
        logs = LigaPointLog.objects.filter(participant__student=student).select_related('participant__season')
        season = request.query_params.get('season')
        if season and season.isdigit():
            logs = logs.filter(participant__season_id=int(season))
        source = request.query_params.get('source')
        if source in dict(LigaPointLog.SOURCES):
            logs = logs.filter(source=source)

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(logs.order_by('-created_at', '-id'), request, view=self)
        return paginator.get_paginated_response([
            {
                'id': log.id,
                'season': log.participant.season.number,
                'source': log.source,
                'points': log.points,
                'created_at': log.created_at,
            }
            for log in page
        ])


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


def _attempts_of(test):
    """Testni ishlaganlar: yakunlaganlar o'rni bilan, ortidan hali ishlayotganlar."""
    services.finalize_expired(test)
    return services.ranked_attempts(test) + list(
        test.attempts.filter(status=LigaAttempt.STATUS_IN_PROGRESS)
        .select_related('student', 'student__user').order_by('started_at')
    )


def _is_found(attempt, search):
    return search in attempt.student.full_name.lower() or search in (attempt.student.user.phone or '')


def _attempt_row(attempt):
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


def _attempts_xlsx(filename, rows, with_grade=False):
    def local(value):
        return timezone.localtime(value).strftime('%d.%m.%Y %H:%M:%S') if value else ''

    def minutes(seconds):
        return f"{seconds // 60:02d}:{seconds % 60:02d}" if seconds is not None else ''

    grade_head = ["Sinf"] if with_grade else []
    return _xlsx(
        filename, "Natijalar",
        grade_head + [
            "O'rin", "F.I.Sh.", "Telefon", "Viloyat", "Tuman", "Maktab", "Holat", "Boshlagan", "Yakunlagan",
            "Ishlagan vaqti", "Savollar", "Javob berilgan", "To'g'ri", "Noto'g'ri", "Gol", "Maksimal gol",
        ],
        [
            ([row['grade']] if with_grade else []) + [
                row['rank'], row['full_name'], row['phone'], row['region'], row['district'], row['school'],
                row['status'], local(row['started_at']), local(row['finished_at']), minutes(row['duration_seconds']),
                row['total_questions'], row['answered_count'], row['correct_count'], row['wrong_count'],
                row['score'], row['max_score'],
            ]
            for row in rows
        ],
    )


class AdminAttemptDetailAPIView(APIView):
    """Mentor/admin: o'quvchi natijasini ochganda — har bir savol, belgilagan javobi, to'g'ri javob va goli."""
    permission_classes = [IsLigaAdmin]

    def get(self, request, attempt_id):
        attempt = get_object_or_404(
            LigaAttempt.objects.select_related('test', 'test__grade', 'test__season', 'student', 'student__user'),
            id=attempt_id,
        )
        attempt = services.finalize_if_expired(attempt)
        data = _attempt_row(attempt)
        data.update({
            'test': attempt.test_id,
            'season_number': attempt.test.season.number,
            'week_number': attempt.test.week_number,
            'grade': attempt.test.grade.name,
        })
        if attempt.status != LigaAttempt.STATUS_IN_PROGRESS:
            data['by_subject'] = _subject_stats(attempt)
            data.update(_review_block(attempt, request, force=True))
        return Response(data)


def _point_rows(logs):
    """Ball yozuvlari tafsiloti bilan: kunlik kirish — sana, fan — qaysi fan/mavzu savoli, test — qaysi hafta va natija."""
    source_labels = dict(LigaPointLog.SOURCES)
    refs = {source: [log.ref for log in logs if log.source == source and log.ref.isdigit()] for source in source_labels}
    score_logs = {
        str(item.id): item
        for item in StudentScoreLog.objects.filter(id__in=refs[LigaPointLog.SOURCE_SUBJECT])
        .select_related('question__topic__chapter__subject')
    }
    attempts = {
        str(item.id): item
        for item in LigaAttempt.objects.filter(id__in=refs[LigaPointLog.SOURCE_TEST]).select_related('test')
    }

    rows = []
    for log in logs:
        detail, attempt_id = '', None
        if log.source == LigaPointLog.SOURCE_DAILY:
            detail = f"{log.ref} kuni ilovaga/saytga kirgani uchun"
        elif log.source == LigaPointLog.SOURCE_SUBJECT:
            item = score_logs.get(log.ref)
            if item:
                topic = item.question.topic
                subject = topic.chapter.subject.name if topic.chapter and topic.chapter.subject else ''
                detail = f"{subject} — {topic.name} (savol #{item.question_id})".lstrip(' —')
            else:
                detail = f"Savol yechgani uchun (#{log.ref})"
        elif log.source == LigaPointLog.SOURCE_TEST:
            item = attempts.get(log.ref)
            if item:
                attempt_id = item.id
                detail = (
                    f"{item.test.week_number}-hafta testi: {item.correct_count}/{item.total_questions} to'g'ri, "
                    f"{item.score}/{item.max_score} gol"
                )
            else:
                detail = "Haftalik test"
        rows.append({
            'id': log.id,
            'source': log.source,
            'source_label': source_labels.get(log.source, log.source),
            'detail': detail,
            'attempt_id': attempt_id,
            'points': log.points,
            'created_at': log.created_at,
        })
    return rows


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


class AdminSeasonViewSet(viewsets.ModelViewSet):
    queryset = LigaSeason.objects.all()
    serializer_class = AdminSeasonSerializer
    permission_classes = [IsLigaAdmin]

    def destroy(self, request, *args, **kwargs):
        """Mavsum unga bog'liq hamma narsa bilan o'chadi (oldindan ogohlantiriladi)."""
        info = services.delete_season(self.get_object())
        return Response({'deleted': True, **info})

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

    @action(detail=True, methods=['get'])
    def points(self, request, pk=None):
        """O'quvchining mavsum ballari qayerdan kelgani: ?student=, ?source=daily|subject|test, ?page=, ?page_size=20"""
        season = self.get_object()
        student_id = request.query_params.get('student') or ''
        if not student_id.isdigit():
            raise ValidationError({'message': "O'quvchini ko'rsating"})
        participant = get_object_or_404(
            LigaParticipant.objects.select_related('student', 'student__user', 'grade'),
            season=season, student_id=int(student_id),
        )

        all_logs = LigaPointLog.objects.filter(participant=participant)
        summary = {
            row['source']: {'points': row['points'] or 0, 'count': row['count']}
            for row in all_logs.values('source').annotate(points=Sum('points'), count=Count('id'))
        }
        logs = all_logs
        source = request.query_params.get('source')
        if source in dict(LigaPointLog.SOURCES):
            logs = logs.filter(source=source)

        paginator = StandardResultsSetPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(logs.order_by('-created_at', '-id'), request, view=self)
        response = paginator.get_paginated_response(_point_rows(page))
        response.data['participant'] = {
            'student_id': participant.student_id,
            'full_name': participant.student.full_name,
            'phone': participant.student.user.phone,
            'grade': participant.grade.name,
            'points': participant.points,
            'joined_at': participant.joined_at,
        }
        response.data['summary'] = [
            {'source': key, 'label': label, **summary.get(key, {'points': 0, 'count': 0})}
            for key, label in LigaPointLog.SOURCES
        ]
        return response

    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Shu hafta testini ishlaganlar, sinflar bo'yicha: ?week=, ?grade=, ?search=, ?export=xlsx"""
        season = self.get_object()
        week = request.query_params.get('week') or ''
        if not week.isdigit():
            raise ValidationError({'message': "Hafta raqamini ko'rsating"})

        tests = season.tests.filter(week_number=week).select_related('grade').order_by('grade_id')
        grade_id = request.query_params.get('grade')
        if grade_id:
            tests = tests.filter(grade_id=grade_id)
        search = (request.query_params.get('search') or '').strip().lower()

        data = [
            {**_attempt_row(attempt), 'grade': test.grade.name}
            for test in tests
            for attempt in _attempts_of(test)
            if not search or _is_found(attempt, search)
        ]
        if request.query_params.get('export') == 'xlsx':
            return _attempts_xlsx(f'liga_{season.number}_{week}_hafta', data, with_grade=True)

        paginator = StandardResultsSetPagination()
        return paginator.get_paginated_response(paginator.paginate_queryset(data, request, view=self))


WEEK_FIELDS = ('week_number', 'start_at', 'end_at', 'duration_minutes', 'question_count')


class AdminTestViewSet(viewsets.ModelViewSet):
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

    def destroy(self, request, *args, **kwargs):
        """Test savollari, o'quvchilar natijalari va shu test uchun berilgan liga ballari bilan o'chadi."""
        info = services.delete_tests([self.get_object().id])
        return Response({'deleted': True, **info})

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

    @action(detail=False, methods=['patch', 'delete'])
    def week(self, request):
        """Haftaning hamma sinflardagi testlari birga: ?season=1&week_number=2"""
        params = WeekSerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        tests = LigaTest.objects.filter(**params.validated_data)
        if not tests.exists():
            return Response({'message': "Bu haftada testlar yo'q"}, status=404)

        if request.method == 'DELETE':
            info = services.delete_tests(tests.values_list('id', flat=True))
            return Response({'deleted': True, **info})

        changes = {name: request.data[name] for name in WEEK_FIELDS if name in request.data}
        with transaction.atomic():
            for test in tests:
                serializer = AdminTestSerializer(test, data=changes, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()
        return Response({'updated': len(tests)})

    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Testni ishlaganlar: o'rni, vaqti va natijasi. ?search=, ?status=, ?export=xlsx"""
        test = self.get_object()
        rows = _attempts_of(test)

        status_filter = request.query_params.get('status')
        if status_filter:
            rows = [item for item in rows if item.status == status_filter]
        search = (request.query_params.get('search') or '').strip().lower()
        if search:
            rows = [item for item in rows if _is_found(item, search)]

        data = [_attempt_row(item) for item in rows]
        if request.query_params.get('export') == 'xlsx':
            return _attempts_xlsx(f'liga_test_{test.id}', data)

        paginator = StandardResultsSetPagination()
        return paginator.get_paginated_response(paginator.paginate_queryset(data, request, view=self))


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
