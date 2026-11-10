"""Liga mantig'i: qo'shilish, ballar, test ishlash, o'rinlar va mavsumni yopish.
Vaqt faqat serverda hisoblanadi — frontend taymeri faqat ko'rsatish uchun."""
import random
from datetime import timedelta

from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from django_app.app_payments.models import Subscription
from django_app.app_student.gol import award_gol
from django_app.app_student.math_answer_check import advanced_math_check
from django_app.app_student.models import StudentPointLog
from django_app.app_user.models import Class

from .models import (
    LigaAnswer, LigaAttempt, LigaChoice, LigaParticipant, LigaPointLog, LigaQuestion, LigaSeason, LigaTest, LigaWinner,
)

WINNERS_PER_GRADE = 3
DAILY_POINTS = 1
SUBJECT_POINTS = 1


class LigaError(Exception):
    """O'quvchiga ko'rsatiladigan xato (400)."""


def student_grade_id(student):
    subject = student.class_name
    return subject.classes_id if subject else None


def is_subscription_active(student):
    """Ligada faqat to'lov qilgan, obunasi amal qilayotgan o'quvchi qatnashadi."""
    now = timezone.now()
    return Subscription.objects.filter(
        student=student, is_paid=True, start_date__lte=now, end_date__gte=now,
    ).exists()


def join_season(season, student, grade_id=None):
    """Ligaga qo'shilish. Sinfni o'quvchi o'zi tanlaydi (sovrin topshirishda hujjat bilan tekshiriladi);
    tanlanmasa — profildagi sinf. Qo'shilgach sinf o'zgarmaydi."""
    if season.is_closed or not season.is_published:
        raise LigaError("Mavsum ochiq emas")
    if grade_id is not None:
        if not Class.objects.filter(pk=grade_id).exists():
            raise LigaError("Sinf noto'g'ri tanlangan")
    else:
        grade_id = student_grade_id(student)
    if not grade_id:
        raise LigaError("Sinfingizni tanlang")
    if not is_subscription_active(student):
        raise LigaError("Ligada qatnashish uchun obuna faol bo'lishi kerak")
    participant, _ = LigaParticipant.objects.get_or_create(
        season=season, student=student, defaults={'grade_id': grade_id},
    )
    return participant


# ---------- Ballar ----------

def award_points(participant, source, ref, points):
    """Takroriy chaqiruv ball qo'shmaydi. Yopilgan mavsumga ball yozilmaydi."""
    if points <= 0 or participant.season.is_closed:
        return False
    with transaction.atomic():
        _, created = LigaPointLog.objects.get_or_create(
            participant=participant, source=source, ref=str(ref), defaults={'points': points},
        )
        if created:
            LigaParticipant.objects.filter(pk=participant.pk).update(points=F('points') + points)
    return created


def _open_participations(student_id):
    return LigaParticipant.objects.filter(
        student_id=student_id, season__closed_at__isnull=True, season__is_published=True,
    ).select_related('season')


def award_daily_login(student_id):
    today = timezone.localdate().isoformat()
    for participant in _open_participations(student_id):
        award_points(participant, LigaPointLog.SOURCE_DAILY, today, DAILY_POINTS)


def award_subject_work(student_id, score_log_id):
    for participant in _open_participations(student_id):
        award_points(participant, LigaPointLog.SOURCE_SUBJECT, score_log_id, SUBJECT_POINTS)


# ---------- Test ishlash ----------

def start_attempt(test, student):
    """Testni boshlaydi yoki boshlangan urinishni qaytaradi: sahifa yopilib qayta ochilsa ham
    o'sha savollar va o'sha taymer davom etadi, testni qaytadan ishlab bo'lmaydi."""
    existing = LigaAttempt.objects.filter(test=test, student=student).first()
    if existing:
        return finalize_if_expired(existing)

    if test.season.is_closed:
        raise LigaError("Mavsum yopilgan")
    if test.status != LigaTest.STATUS_LIVE:
        raise LigaError("Test hozir ochiq emas")

    participant = LigaParticipant.objects.filter(season=test.season, student=student).first()
    if not participant:
        raise LigaError("Avval ligaga qo'shiling")
    if participant.grade_id != test.grade_id:
        raise LigaError("Bu test sizning sinfingiz uchun emas")
    if not is_subscription_active(student):
        raise LigaError("Ligada qatnashish uchun obuna faol bo'lishi kerak")

    pool = list(test.questions.values_list('id', flat=True))
    if not pool:
        raise LigaError("Testda savollar yo'q")
    # Har bir o'quvchiga bazadan tasodifiy question_count ta savol tushadi
    question_ids = random.sample(pool, min(test.question_count, len(pool)))

    now = timezone.now()
    attempt, _ = LigaAttempt.objects.get_or_create(
        test=test, student=student,
        defaults={
            'question_order': question_ids,
            'total_questions': len(question_ids),
            # Kech kirgan o'quvchi test oynasi yopilishidan keyin ishlay olmaydi
            'deadline_at': min(now + timedelta(minutes=test.duration_minutes), test.end_at),
        },
    )
    return attempt


def _is_correct(question, choice, text_answer):
    if question.question_type == LigaQuestion.TYPE_CHOICE:
        return bool(choice and choice.is_correct)
    return advanced_math_check(text_answer, (question.correct_text_answer or '').strip())


def save_answer(attempt_id, question_id, choice_id=None, text_answer=None):
    text_answer = (text_answer or '').strip()
    with transaction.atomic():
        attempt = LigaAttempt.objects.select_for_update().get(pk=attempt_id)
        if attempt.status != LigaAttempt.STATUS_IN_PROGRESS:
            raise LigaError("Test yakunlangan")
        expired = timezone.now() >= attempt.deadline_at
        if expired:
            _finalize(attempt, LigaAttempt.STATUS_EXPIRED)
        else:
            question = LigaQuestion.objects.filter(pk=question_id, test_id=attempt.test_id).first()
            if not question or question.id not in attempt.question_order:
                raise LigaError("Savol bu testga tegishli emas")

            choice = None
            if question.question_type == LigaQuestion.TYPE_CHOICE:
                choice = LigaChoice.objects.filter(pk=choice_id, question=question).first()
                if not choice:
                    raise LigaError("Variant noto'g'ri")
                text_answer = None
            elif not text_answer:
                raise LigaError("Javob bo'sh")

            answer, _ = LigaAnswer.objects.update_or_create(
                attempt=attempt, question=question,
                defaults={
                    'selected_choice': choice,
                    'text_answer': text_answer,
                    'is_correct': _is_correct(question, choice, text_answer),
                },
            )
    # Tranzaksiyadan tashqarida: aks holda xato bilan birga yakunlash ham bekor bo'lardi
    if expired:
        raise LigaError("Test vaqti tugagan")
    return answer


def _finalize(attempt, status):
    """Faqat qulflangan (select_for_update) urinish bilan chaqiriladi.
    Javob berilmagan savollar uchun ball yo'q, ular xato hisoblanadi."""
    answers = attempt.answers.select_related('question')
    correct = [answer for answer in answers if answer.is_correct]
    finished_at = min(timezone.now(), attempt.deadline_at)

    attempt.status = status
    attempt.finished_at = finished_at
    attempt.duration_seconds = max(0, int((finished_at - attempt.started_at).total_seconds()))
    attempt.answered_count = len(answers)
    attempt.correct_count = len(correct)
    attempt.score = sum(answer.question.score for answer in correct)
    attempt.max_score = (
        LigaQuestion.objects.filter(id__in=attempt.question_order).aggregate(total=Sum('score'))['total'] or 0
    )
    attempt.save()

    participant = (
        LigaParticipant.objects.select_related('season')
        .filter(season_id=attempt.test.season_id, student_id=attempt.student_id).first()
    )
    if participant:
        award_points(participant, LigaPointLog.SOURCE_TEST, attempt.id, attempt.score)

    # Haftalik test uchun gol: to'g'ri javoblar balli (har savol odatda 1) — shuncha gol.
    # Bir urinish uchun bir marta (ref = urinish id), tarixi StudentPointLog'da
    award_gol(
        attempt.student_id,
        StudentPointLog.SOURCE_WEEKLY_TEST,
        attempt.score,
        ref=attempt.id,
        date=timezone.localtime(finished_at).date(),
        comment=f"Haftalik test: {attempt.test} — {attempt.correct_count}/{attempt.total_questions} to'g'ri",
    )
    return attempt


def finish_attempt(attempt_id):
    with transaction.atomic():
        attempt = LigaAttempt.objects.select_for_update().select_related('test').get(pk=attempt_id)
        if attempt.status != LigaAttempt.STATUS_IN_PROGRESS:
            return attempt
        expired = timezone.now() >= attempt.deadline_at
        return _finalize(attempt, LigaAttempt.STATUS_EXPIRED if expired else LigaAttempt.STATUS_FINISHED)


def finalize_if_expired(attempt):
    if attempt.status != LigaAttempt.STATUS_IN_PROGRESS or timezone.now() < attempt.deadline_at:
        return attempt
    return finish_attempt(attempt.id)


def finalize_expired(test=None, season=None):
    """Vaqti tugab, "Yakunlash"ni bosmagan o'quvchilarni yopadi (Celery har daqiqada chaqiradi)."""
    pending = LigaAttempt.objects.filter(status=LigaAttempt.STATUS_IN_PROGRESS, deadline_at__lte=timezone.now())
    if test is not None:
        pending = pending.filter(test=test)
    if season is not None:
        pending = pending.filter(test__season=season)
    ids = list(pending.values_list('id', flat=True))
    for attempt_id in ids:
        finish_attempt(attempt_id)
    return len(ids)


# ---------- O'rinlar ----------

def ranked_attempts(test):
    """Bitta test natijalari: avval ball, teng bo'lsa kam vaqt. Ikkalasi teng bo'lsa o'rin bir xil."""
    attempts = list(
        test.attempts.exclude(status=LigaAttempt.STATUS_IN_PROGRESS)
        .select_related('student', 'student__user')
        .order_by('-score', 'duration_seconds', 'id')
    )
    rank, previous = 0, None
    for index, attempt in enumerate(attempts, start=1):
        key = (attempt.score, attempt.duration_seconds)
        if key != previous:
            rank, previous = index, key
        attempt.rank = rank
    return attempts


def standings(season, grade_id):
    """Sinf reytingi: ko'p ball, teng bo'lsa testlarga kam vaqt, keyin oldin qo'shilgan."""
    participants = list(
        season.participants.filter(grade_id=grade_id)
        .select_related('student', 'student__user')
        .annotate(test_seconds=Sum(
            'student__liga_attempts__duration_seconds',
            filter=Q(student__liga_attempts__test__season=season),
        ))
    )
    participants.sort(key=lambda item: (-item.points, item.test_seconds or 0, item.joined_at))
    for index, participant in enumerate(participants, start=1):
        participant.rank = index
    return participants


# ---------- Mavsumni yopish ----------

def close_season(season_id):
    """G'oliblarni saqlaydi va hammaning liga ballarini nolga tushiradi. Takror chaqirilsa hech narsa qilmaydi."""
    season = LigaSeason.objects.get(pk=season_id)
    finalize_expired(season=season)

    with transaction.atomic():
        season = LigaSeason.objects.select_for_update().get(pk=season_id)
        if season.is_closed:
            return season

        grade_ids = list(season.participants.order_by().values_list('grade_id', flat=True).distinct())
        winners = []
        for grade_id in grade_ids:
            top = [item for item in standings(season, grade_id) if item.points > 0][:WINNERS_PER_GRADE]
            for place, participant in enumerate(top, start=1):
                winners.append(LigaWinner(
                    season=season, grade_id=grade_id, place=place, student=participant.student,
                    points=participant.points,
                    prize_uz=getattr(season, f'prize_{place}_uz'), prize_ru=getattr(season, f'prize_{place}_ru'),
                ))
        LigaWinner.objects.bulk_create(winners)
        season.participants.update(points=0)
        season.closed_at = timezone.now()
        season.save(update_fields=['closed_at'])
    return season


def close_finished_seasons():
    """Oxirgi hafta testlari tugagan mavsumlarni yopadi (Celery har daqiqada chaqiradi).
    Haftalar birma-bir qo'shilgani uchun oxirgi hafta weeks_count bo'yicha aniqlanadi."""
    now = timezone.now()
    closed = 0
    for season in LigaSeason.objects.filter(closed_at__isnull=True, is_published=True):
        tests = season.tests.filter(is_published=True)
        last_week = tests.filter(week_number__gte=season.weeks_count)
        if last_week.exists() and not tests.filter(end_at__gt=now).exists():
            close_season(season.id)
            closed += 1
    return closed
