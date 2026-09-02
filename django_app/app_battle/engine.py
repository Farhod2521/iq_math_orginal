"""The match engine: everything that happens once a room has two
participants and questions start flowing. Called from Celery tasks
(tasks.py) and from the WS consumer (consumers.py) — never talks to the
channel layer directly except through realtime.send_event, and every
state transition that can be triggered from two different places (a
timeout task vs. a "both answered" event) is guarded by a row lock so only
one of them ever actually performs the transition.
"""

import random

from django.db import models, transaction
from django.utils import timezone

from django_app.app_teacher.models import Question, Choice
from django_app.app_student.models import StudentScore

from . import elo as elo_module
from .bots import pick_bot_identity, pick_bot_difficulty, bot_elo_before
from .grading import check_answer
from .models import (
    BattleRoom, BattleParticipant, BattleRoomQuestion, BattleAnswer,
    BattleRating, BattleEloLog,
)
from .realtime import send_event
from .serializers import serialize_room_snapshot, serialize_question

BATTLE_WIN_SCORE_REWARD = 3
BATTLE_WIN_COIN_REWARD = 2


def snapshot_questions(room):
    # No difficulty filter on purpose: nobody knows in advance whether the
    # opponent (real or bot) is strong or weak, so questions are drawn
    # across every level within the selected subjects — difficulty comes up
    # random per question rather than being a pre-match user choice.
    questions = list(
        Question.objects.filter(topic__chapter__subject__in=room.subjects.all()).distinct()
    )
    count = min(room.question_count, len(questions))
    picked = random.sample(questions, count) if count else []
    BattleRoomQuestion.objects.bulk_create([
        BattleRoomQuestion(room=room, question=q, order=i) for i, q in enumerate(picked)
    ])
    if count != room.question_count:
        room.question_count = count
        room.save(update_fields=['question_count'])
    return count


def start_match(room):
    snapshot_questions(room)
    room.status = BattleRoom.STATUS_ACTIVE
    room.started_at = timezone.now()
    room.current_question_index = 0
    room.current_question_started_at = timezone.now()
    room.save(update_fields=[
        'status', 'started_at', 'current_question_index', 'current_question_started_at',
    ])

    first_question = room.questions.filter(order=0).first()
    send_event(room.id, 'battle_started', {
        'room': serialize_room_snapshot(room),
        'question': serialize_question(first_question),
    })
    _arm_question_timers(room, 0)


def _arm_question_timers(room, index):
    from .tasks import advance_question_if_timeout, bot_answer_question

    advance_question_if_timeout.apply_async(
        args=[room.id, index], countdown=room.seconds_per_question,
    )
    bot_participant = room.participants.filter(bot_identity__isnull=False).select_related('bot_difficulty').first()
    if bot_participant and bot_participant.bot_difficulty_id:
        delay = bot_participant.bot_difficulty.random_answer_delay()
        delay = min(delay, max(room.seconds_per_question - 1, 1))
        bot_answer_question.apply_async(
            args=[room.id, index, bot_participant.id], countdown=delay,
        )


def maybe_inject_bot(room_id):
    try:
        room = BattleRoom.objects.select_related('grade').get(id=room_id)
    except BattleRoom.DoesNotExist:
        return
    if room.status != BattleRoom.STATUS_WAITING:
        return  # a human joined during the wait — nothing to do

    student_participant = room.participants.filter(student__isnull=False).first()
    if not student_participant:
        return

    rating, _ = BattleRating.objects.get_or_create(student=student_participant.student)
    identity = pick_bot_identity(student_participant.student)
    difficulty = pick_bot_difficulty(rating)
    if identity is None or difficulty is None:
        return  # bots not seeded yet — leave the room waiting for a human

    BattleParticipant.objects.create(
        room=room, bot_identity=identity, bot_difficulty=difficulty,
        elo_before=bot_elo_before(rating.elo),
    )
    start_match(room)


def _bot_answer_payload(question, want_correct):
    if question.question_type in ('choice', 'image_choice'):
        correct_ids = list(Choice.objects.filter(question=question, is_correct=True).values_list('id', flat=True))
        if want_correct:
            return {'choices': correct_ids}
        wrong_pool = list(
            Choice.objects.filter(question=question).exclude(id__in=correct_ids).values_list('id', flat=True)
        )
        return {'choices': [random.choice(wrong_pool)] if wrong_pool else correct_ids}

    if question.question_type == 'text':
        if want_correct:
            return {'answer_uz': (question.correct_text_answer_uz or '').strip()}
        return {'answer_uz': '???'}

    if question.question_type == 'composite':
        subs = list(question.sub_questions.order_by('id'))
        if want_correct:
            return {'answers': [s.correct_answer for s in subs]}
        return {'answers': ['0'] * len(subs)}

    return {}


def bot_answer_question(room_id, question_order, participant_id):
    try:
        participant = BattleParticipant.objects.select_related('bot_difficulty').get(id=participant_id)
    except BattleParticipant.DoesNotExist:
        return
    if not participant.is_bot or not participant.bot_difficulty_id:
        return

    room = BattleRoom.objects.filter(id=room_id).first()
    if not room or room.status != BattleRoom.STATUS_ACTIVE or room.current_question_index != question_order:
        return

    try:
        room_question = room.questions.get(order=question_order)
    except BattleRoomQuestion.DoesNotExist:
        return

    want_correct = participant.bot_difficulty.roll_correct()
    raw_answer = _bot_answer_payload(room_question.question, want_correct)
    record_answer(room_id, participant.id, question_order, raw_answer, skipped=False)


def record_answer(room_id, participant_id, question_order, raw_answer, skipped=False):
    room = BattleRoom.objects.filter(id=room_id).first()
    if not room or room.status != BattleRoom.STATUS_ACTIVE or room.current_question_index != question_order:
        return  # stale/late submission for a question that's already moved on

    try:
        room_question = room.questions.get(order=question_order)
    except BattleRoomQuestion.DoesNotExist:
        return

    try:
        participant = room.participants.get(id=participant_id)
    except BattleParticipant.DoesNotExist:
        return

    elapsed = room.seconds_per_question
    if room.current_question_started_at:
        elapsed = (timezone.now() - room.current_question_started_at).total_seconds()
    elapsed = max(0.0, min(elapsed, room.seconds_per_question))

    is_correct = False if skipped else check_answer(room_question.question, raw_answer)
    _, created = BattleAnswer.objects.get_or_create(
        room_question=room_question, participant=participant,
        defaults={
            'raw_answer': raw_answer, 'is_correct': is_correct,
            'answer_time_seconds': elapsed, 'skipped': skipped,
        },
    )
    if not created:
        return  # already answered this question — ignore duplicate/late submits

    if is_correct:
        BattleParticipant.objects.filter(id=participant.id).update(score=models.F('score') + 1)
    BattleParticipant.objects.filter(id=participant.id).update(
        total_answer_time=models.F('total_answer_time') + elapsed
    )

    send_event(room_id, 'opponent_progress', {
        'participant_id': participant.id, 'answered': True, 'skipped': skipped,
    })

    both_answered = (
        BattleAnswer.objects.filter(room_question=room_question).count() >= room.participants.count()
    )
    if both_answered:
        advance_to_next_question(room_id, question_order)


def advance_to_next_question(room_id, expected_index):
    is_finished = False
    next_room_question = None
    room = None

    with transaction.atomic():
        room = BattleRoom.objects.select_for_update().get(id=room_id)
        if room.status != BattleRoom.STATUS_ACTIVE or room.current_question_index != expected_index:
            return  # already advanced via the other trigger — no-op

        room_question = room.questions.get(order=expected_index)
        answered_ids = set(
            BattleAnswer.objects.filter(room_question=room_question).values_list('participant_id', flat=True)
        )
        for participant in room.participants.all():
            if participant.id not in answered_ids:
                BattleAnswer.objects.get_or_create(
                    room_question=room_question, participant=participant,
                    defaults={
                        'is_correct': False, 'answer_time_seconds': room.seconds_per_question, 'skipped': True,
                    },
                )

        next_index = expected_index + 1
        is_finished = next_index >= room.question_count
        room.current_question_index = next_index
        room.current_question_started_at = None if is_finished else timezone.now()
        room.save(update_fields=['current_question_index', 'current_question_started_at'])
        if not is_finished:
            next_room_question = room.questions.filter(order=next_index).first()

    if is_finished:
        finish_battle(room_id)
        return

    send_event(room_id, 'next_question', {
        'index': room.current_question_index,
        'question': serialize_question(next_room_question),
    })
    _arm_question_timers(room, room.current_question_index)


def _avg_seconds_on_correct(participant, room):
    times = list(
        BattleAnswer.objects.filter(
            room_question__room=room, participant=participant, is_correct=True, skipped=False,
        ).values_list('answer_time_seconds', flat=True)
    )
    return (sum(times) / len(times)) if times else None


def _award_battle_win_reward(student):
    student_score, _ = StudentScore.objects.get_or_create(student=student)
    student_score.score += BATTLE_WIN_SCORE_REWARD
    student_score.coin += BATTLE_WIN_COIN_REWARD
    student_score.save(update_fields=['score', 'coin'])


def finish_battle(room_id):
    results_payload = []
    winner_id = None

    with transaction.atomic():
        room = BattleRoom.objects.select_for_update().get(id=room_id)
        if room.status != BattleRoom.STATUS_ACTIVE:
            return

        participants = list(
            room.participants.select_related('student', 'bot_identity', 'bot_difficulty').all()
        )
        if len(participants) != 2:
            room.status = BattleRoom.STATUS_CANCELLED
            room.finished_at = timezone.now()
            room.save(update_fields=['status', 'finished_at'])
            send_event(room_id, 'battle_voided', {'reason': 'incomplete'})
            return

        a, b = participants
        result_a, result_b = elo_module.match_outcome(a.score, a.total_answer_time, b.score, b.total_answer_time)

        winner = None
        for participant, opponent, result in ((a, b, result_a), (b, a, result_b)):
            avg_correct_time = _avg_seconds_on_correct(participant, room)
            performance = elo_module.performance_score(
                participant.score, room.question_count, avg_correct_time, room.seconds_per_question,
            )

            if participant.is_bot:
                elo_after = participant.elo_before
                elo_change = 0
            else:
                rating, _ = BattleRating.objects.select_for_update().get_or_create(student=participant.student)
                k = rating.k_factor()
                elo_change = elo_module.compute_elo_delta(
                    participant.elo_before, opponent.elo_before, result, k, performance,
                )
                elo_after = max(0, participant.elo_before + elo_change)
                rating.apply_result(elo_after, result)
                BattleEloLog.objects.create(
                    student=participant.student, room=room,
                    elo_before=participant.elo_before, elo_after=elo_after,
                    elo_change=elo_change, result=result,
                )
                if result == 'win':
                    _award_battle_win_reward(participant.student)

            participant.elo_after = elo_after
            participant.save(update_fields=['elo_after'])
            if result == 'win':
                winner = participant

            results_payload.append({
                'participant_id': participant.id,
                'result': result,
                'score': participant.score,
                'elo_before': participant.elo_before,
                'elo_after': elo_after,
                'elo_change': elo_change,
            })

        winner_id = winner.id if winner else None
        room.status = BattleRoom.STATUS_FINISHED
        room.finished_at = timezone.now()
        room.winner_participant_id = winner_id
        room.save(update_fields=['status', 'finished_at', 'winner_participant'])

    send_event(room_id, 'battle_finished', {'results': results_payload, 'winner_participant_id': winner_id})


def void_room_for_disconnect(room_id, participant_id):
    with transaction.atomic():
        room = BattleRoom.objects.select_for_update().get(id=room_id)
        if room.status != BattleRoom.STATUS_ACTIVE:
            return
        try:
            participant = room.participants.get(id=participant_id)
        except BattleParticipant.DoesNotExist:
            return
        if participant.left_at is None:
            return  # reconnected in time

        room.status = BattleRoom.STATUS_CANCELLED
        room.finished_at = timezone.now()
        room.save(update_fields=['status', 'finished_at'])

    send_event(room_id, 'battle_voided', {'reason': 'disconnect'})


def record_chat_message(room_id, participant_id, text):
    room = BattleRoom.objects.filter(id=room_id).first()
    if not room or not room.chat_enabled:
        return
    try:
        participant = BattleParticipant.objects.get(id=participant_id)
    except BattleParticipant.DoesNotExist:
        return
    send_event(room_id, 'chat_message', {
        'participant_id': participant.id,
        'name': participant.display_name,
        'text': text[:500],
        'created_at': timezone.now().isoformat(),
    })
