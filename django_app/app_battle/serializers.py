from rest_framework import serializers

from django_app.app_student.serializers import CustomQuestionSerializer

from .models import BattleRating, level_for_elo


def serialize_participant(participant, viewer_student=None):
    """Never emit anything that reveals bot-ness — name/elo/level must be
    indistinguishable in shape from a real student's."""
    is_self = (
        viewer_student is not None
        and not participant.is_bot
        and participant.student_id == viewer_student.id
    )
    if participant.is_bot:
        is_placement = False
    else:
        rating, _ = BattleRating.objects.get_or_create(student=participant.student)
        is_placement = rating.is_in_placement

    return {
        'participant_id': participant.id,
        'name': participant.display_name,
        'elo': participant.elo_before,
        'level': level_for_elo(participant.elo_before),
        'is_placement': is_placement,
        'score': participant.score,
        'is_creator': participant.is_creator,
        'is_self': is_self,
    }


def serialize_room_snapshot(room, viewer_student=None):
    return {
        'id': room.id,
        'code': room.code,
        'status': room.status,
        'grade': room.grade.name,
        'subjects': [s.name for s in room.subjects.all()],
        'question_count': room.question_count,
        'seconds_per_question': room.seconds_per_question,
        'chat_enabled': room.chat_enabled,
        'current_question_index': room.current_question_index,
        'participants': [serialize_participant(p, viewer_student) for p in room.participants.all()],
    }


def serialize_question(room_question):
    if room_question is None:
        return None
    return {
        'order': room_question.order,
        'question': CustomQuestionSerializer(room_question.question).data,
    }


class RoomCreateSerializer(serializers.Serializer):
    grade_id = serializers.IntegerField()
    subject_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False, min_length=1)
    question_count = serializers.IntegerField(default=10, min_value=1, max_value=30)
    seconds_per_question = serializers.IntegerField(default=60, min_value=10, max_value=300)


class RoomJoinSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=8)
