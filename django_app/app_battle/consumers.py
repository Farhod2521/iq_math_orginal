import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from .models import BattleRoom, BattleParticipant
from .serializers import serialize_room_snapshot, serialize_question
from . import engine

logger = logging.getLogger(__name__)


class BattleConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.group_name = f"battle_{self.room_id}"
        self.student = None
        self.participant = None
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            logger.warning("Battle WS reject unauthenticated room_id=%s", self.room_id)
            await self.close()
            return

        self.student = await database_sync_to_async(self._get_student)(user)
        if not self.student:
            await self.close()
            return

        self.participant = await database_sync_to_async(self._get_participant)()
        if not self.participant:
            logger.warning("Battle WS reject non-participant user_id=%s room_id=%s", user.id, self.room_id)
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await database_sync_to_async(self._clear_disconnect_marker)()

        snapshot = await database_sync_to_async(self._get_room_snapshot)()
        if snapshot:
            await self.send(text_data=json.dumps({
                "event": "room_snapshot",
                "payload": snapshot,
            }))

    async def disconnect(self, close_code):
        if getattr(self, 'group_name', None):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if getattr(self, 'participant', None):
            await database_sync_to_async(self._mark_disconnected)()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")

        if msg_type == "answer":
            await database_sync_to_async(engine.record_answer)(
                self.room_id, self.participant.id, data.get("question_order"),
                data.get("answer"), False,
            )
        elif msg_type == "skip":
            await database_sync_to_async(engine.record_answer)(
                self.room_id, self.participant.id, data.get("question_order"),
                None, True,
            )
        elif msg_type == "chat":
            text = (data.get("text") or "").strip()
            if text:
                await database_sync_to_async(engine.record_chat_message)(
                    self.room_id, self.participant.id, text,
                )
        elif msg_type == "timeout_check":
            # Client-side self-heal: the browser's own countdown hit zero
            # with no `next_question` event ever arriving — nudge the
            # server to advance in case the scheduled Celery timeout task
            # was lost (worker restart, broker hiccup, etc). Safe to call
            # redundantly: advance_to_next_question no-ops if the question
            # already moved on.
            await database_sync_to_async(engine.advance_to_next_question)(
                self.room_id, data.get("question_order"),
            )

    async def battle_event(self, event):
        await self.send(text_data=json.dumps({
            "event": event["event"],
            "payload": event["payload"],
        }))

    # -- sync DB helpers, run via database_sync_to_async --

    def _get_student(self, user):
        from django_app.app_user.models import Student
        return Student.objects.filter(user=user).first()

    def _get_room_snapshot(self):
        # Built entirely inside this sync-wrapped call: serialize_room_snapshot
        # touches lazy relations (subjects M2M, bot_identity FK, BattleRating
        # lookups) that must not run directly in the consumer's async context.
        room = BattleRoom.objects.filter(id=self.room_id).select_related('grade').first()
        if not room:
            return None

        if room.status == BattleRoom.STATUS_ACTIVE and room.current_question_started_at:
            elapsed = (timezone.now() - room.current_question_started_at).total_seconds()
            if elapsed >= room.seconds_per_question:
                # The scheduled Celery timeout task appears to have been
                # lost (worker restart, broker hiccup, etc.) — self-heal on
                # (re)connect rather than leaving the match stuck forever.
                engine.advance_to_next_question(room.id, room.current_question_index)
                room = BattleRoom.objects.filter(id=self.room_id).select_related('grade').first()

        snapshot = serialize_room_snapshot(room, self.student)

        # A (re)connect must be able to recover an in-progress match on its
        # own — `room_snapshot` alone used to carry no question data, so any
        # reconnect (page refresh, a duplicate WS mount, etc.) left the
        # client stuck on a spinner forever with no further event to fix it.
        if room.status == BattleRoom.STATUS_ACTIVE:
            current_room_question = room.questions.filter(order=room.current_question_index).first()
            snapshot['current_question'] = serialize_question(current_room_question)
            snapshot['question_seconds_elapsed'] = (
                (timezone.now() - room.current_question_started_at).total_seconds()
                if room.current_question_started_at else 0
            )
        else:
            snapshot['current_question'] = None
            snapshot['question_seconds_elapsed'] = 0

        return snapshot

    def _get_participant(self):
        return BattleParticipant.objects.filter(room_id=self.room_id, student=self.student).first()

    def _clear_disconnect_marker(self):
        BattleParticipant.objects.filter(id=self.participant.id).update(left_at=None)

    def _mark_disconnected(self):
        BattleParticipant.objects.filter(id=self.participant.id).update(left_at=timezone.now())
        room = BattleRoom.objects.filter(id=self.room_id).first()
        if room and room.status == BattleRoom.STATUS_ACTIVE:
            from .tasks import void_room_if_still_disconnected
            void_room_if_still_disconnected.apply_async(
                args=[self.room_id, self.participant.id], countdown=20,
            )
