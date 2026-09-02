from celery import shared_task


@shared_task
def maybe_inject_bot(room_id):
    from . import engine
    engine.maybe_inject_bot(room_id)


@shared_task
def bot_answer_question(room_id, question_order, participant_id):
    from . import engine
    engine.bot_answer_question(room_id, question_order, participant_id)


@shared_task
def advance_question_if_timeout(room_id, expected_index):
    from . import engine
    engine.advance_to_next_question(room_id, expected_index)


@shared_task
def void_room_if_still_disconnected(room_id, participant_id):
    from . import engine
    engine.void_room_for_disconnect(room_id, participant_id)
