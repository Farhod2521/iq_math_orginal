"""Room creation / matchmaking. The only place that decides *whether* two
students get paired or a bot gets scheduled — actual match start/question
flow lives in engine.py.

Every room is public random-matchmaking with chat always on (no user-facing
toggles) — the only alternative entry point is joining an existing waiting
room by its share code, via `join_room_by_code`.
"""

import hashlib

from django.conf import settings
from django.db import connection, transaction

from .models import BattleRoom, BattleParticipant, BattleRating, compute_subjects_key
from . import engine

DEFAULT_BOT_INJECT_DELAY_SECONDS = 15  # chess.com-style: real opponent gets ~15s to show up first
PLACEMENT_BOT_DELAY_SECONDS = 3  # short "searching" UX beat, always resolves to a bot


class RoomFull(Exception):
    pass


class RoomNotJoinable(Exception):
    pass


def _advisory_lock_key(grade_id, subjects_key, question_count, seconds_per_question):
    raw = f"{grade_id}:{subjects_key}:{question_count}:{seconds_per_question}"
    digest = hashlib.sha1(raw.encode()).hexdigest()
    # Postgres advisory locks take a 64-bit signed int; fold the hash down.
    return int(digest[:15], 16) - (1 << 59)


def _take_matchmaking_lock(key):
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [key])
    # SQLite (local dev) serializes writers at the database-file level for
    # the duration of a write transaction, which is sufficient outside of
    # production/Postgres.


def create_participant_for_student(room, student, is_creator=False):
    rating, _ = BattleRating.objects.get_or_create(student=student)
    return BattleParticipant.objects.create(
        room=room, student=student, is_creator=is_creator, elo_before=rating.elo,
    )


def _new_room(grade, subjects, subjects_key, question_count, seconds_per_question):
    room = BattleRoom.objects.create(
        grade=grade, subjects_key=subjects_key,
        question_count=question_count, seconds_per_question=seconds_per_question,
        is_random=True, chat_enabled=True, status=BattleRoom.STATUS_WAITING,
    )
    room.subjects.set(subjects)
    return room


def find_or_create_room(student, *, grade, subjects, question_count, seconds_per_question):
    """Returns (room, matched_immediately). Question difficulty is never a
    user choice — engine.snapshot_questions draws from every level within
    the selected subjects, so difficulty comes up random per question,
    matching a real opponent's unpredictable strength."""
    from .tasks import maybe_inject_bot

    subject_ids = [s.id for s in subjects]
    subjects_key = compute_subjects_key(subject_ids)
    rating, _ = BattleRating.objects.get_or_create(student=student)

    if rating.is_in_placement:
        room = _new_room(grade, subjects, subjects_key, question_count, seconds_per_question)
        create_participant_for_student(room, student, is_creator=True)
        maybe_inject_bot.apply_async(args=[room.id], countdown=PLACEMENT_BOT_DELAY_SECONDS)
        return room, False

    lock_key = _advisory_lock_key(grade.id, subjects_key, question_count, seconds_per_question)
    matched_room = None
    with transaction.atomic():
        _take_matchmaking_lock(lock_key)
        existing = (
            BattleRoom.objects.select_for_update()
            .filter(
                status=BattleRoom.STATUS_WAITING, is_random=True,
                grade=grade, subjects_key=subjects_key,
                question_count=question_count, seconds_per_question=seconds_per_question,
            )
            .exclude(participants__student=student)
            .order_by('created_at')
            .first()
        )
        if existing:
            create_participant_for_student(existing, student, is_creator=False)
            matched_room = existing
        else:
            room = _new_room(grade, subjects, subjects_key, question_count, seconds_per_question)
            create_participant_for_student(room, student, is_creator=True)

    if matched_room:
        engine.start_match(matched_room)
        return matched_room, True

    delay = getattr(settings, 'BATTLE_BOT_INJECT_DELAY_SECONDS', DEFAULT_BOT_INJECT_DELAY_SECONDS)
    maybe_inject_bot.apply_async(args=[room.id], countdown=delay)
    return room, False


def join_room_by_code(student, code):
    with transaction.atomic():
        try:
            room = BattleRoom.objects.select_for_update().get(code=code.upper())
        except BattleRoom.DoesNotExist:
            raise RoomNotJoinable("Bunday kodli xona topilmadi")

        if room.status != BattleRoom.STATUS_WAITING:
            raise RoomNotJoinable("Xona endi mavjud emas")
        if room.participants.filter(student=student).exists():
            return room, False
        if room.is_full:
            raise RoomFull("Xona to'lgan")

        create_participant_for_student(room, student, is_creator=False)

    engine.start_match(room)
    return room, True


def cancel_room(student, room):
    if room.status != BattleRoom.STATUS_WAITING:
        raise RoomNotJoinable("Faqat kutilayotgan xonani bekor qilish mumkin")
    if not room.participants.filter(student=student).exists():
        raise RoomNotJoinable("Siz bu xonaning ishtirokchisi emassiz")
    room.status = BattleRoom.STATUS_CANCELLED
    room.save(update_fields=['status'])
    return room
