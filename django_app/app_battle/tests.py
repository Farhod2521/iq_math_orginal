# -*- coding: utf-8 -*-
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from django_app.app_user.models import User, Student, Class, Subject, Subject_Category
from django_app.app_teacher.models import Chapter, Topic, Question, Choice

from . import elo, engine, matchmaking
from .models import BattleRoom, BattleRoomQuestion, BattleRating, compute_subjects_key


class EloFormulaTests(SimpleTestCase):
    """Covers exactly the cases called out in the implementation plan's
    verification section."""

    def test_dominant_win_yields_more_than_narrow_win(self):
        # Equal ELOs (expected = 0.5 each), K=30.
        dominant = elo.compute_elo_delta(1000, 1000, 'win', k=30, performance=1.0)
        narrow = elo.compute_elo_delta(1000, 1000, 'win', k=30, performance=0.0)
        self.assertGreater(dominant, narrow)
        self.assertGreaterEqual(narrow, elo.MIN_DELTA)
        self.assertLessEqual(dominant, elo.MAX_DELTA)

    def test_winner_never_loses_elo_and_loser_never_gains(self):
        for elo_self, elo_opp, perf in [(1000, 1000, 1.0), (700, 1300, 0.2), (1600, 900, 0.9)]:
            win_delta = elo.compute_elo_delta(elo_self, elo_opp, 'win', k=30, performance=perf)
            loss_delta = elo.compute_elo_delta(elo_self, elo_opp, 'loss', k=30, performance=perf)
            self.assertGreaterEqual(win_delta, 0, f"win must not lose ELO ({elo_self} vs {elo_opp})")
            self.assertLessEqual(loss_delta, 0, f"loss must not gain ELO ({elo_self} vs {elo_opp})")

    def test_draw_between_equal_elos_is_a_coin_flip_no_change(self):
        delta = elo.compute_elo_delta(1200, 1200, 'draw', k=30, performance=0.5)
        self.assertEqual(delta, 0)

    def test_draw_between_mismatched_elos_moves_underdog_up_favorite_down(self):
        underdog_delta = elo.compute_elo_delta(900, 1300, 'draw', k=30, performance=0.5)
        favorite_delta = elo.compute_elo_delta(1300, 900, 'draw', k=30, performance=0.5)
        self.assertGreater(underdog_delta, 0)
        self.assertLess(favorite_delta, 0)

    def test_delta_always_clamped(self):
        for elo_self, elo_opp in [(0, 3000), (3000, 0), (1500, 1500)]:
            for result in ('win', 'loss', 'draw'):
                delta = elo.compute_elo_delta(elo_self, elo_opp, result, k=70, performance=1.6)
                self.assertLessEqual(abs(delta), elo.MAX_DELTA)


class BattleFixtureMixin:
    def _make_class(self, name='7'):
        return Class.objects.create(name=name)

    def _make_subject_with_questions(self, klass, level=1, question_count=3, name='Algebra'):
        category = Subject_Category.objects.create(name=name)
        subject = Subject.objects.create(name=name, classes=klass, category=category)
        chapter = Chapter.objects.create(name='Tenglamalar', subject=subject)
        topic = Topic.objects.create(name='Chiziqli tenglamalar', chapter=chapter)
        for i in range(question_count):
            question = Question.objects.create(
                topic=topic, question_text=f"2x + {i} = {i + 2}",
                question_type='choice', level=level,
            )
            Choice.objects.create(question=question, letter='A', text='x=1', is_correct=True)
            Choice.objects.create(question=question, letter='B', text='x=2', is_correct=False)
        return subject

    def _make_room(self, klass, subjects, question_count=3, seconds_per_question=30):
        room = BattleRoom.objects.create(
            grade=klass, subjects_key=compute_subjects_key([s.id for s in subjects]),
            question_count=question_count,
            seconds_per_question=seconds_per_question, is_random=True, chat_enabled=True,
        )
        room.subjects.set(subjects)
        return room

    def _make_student(self, phone, klass):
        user = User.objects.create_user(phone=phone, password='pass12345', role='student')
        subject_for_class = Subject.objects.filter(classes=klass).first()
        return Student.objects.create(user=user, full_name=f"Student {phone}", class_name=subject_for_class)


class MatchmakingTests(BattleFixtureMixin, TestCase):
    def setUp(self):
        from django.core.management import call_command
        call_command('seed_battle_bots', verbosity=0)
        self.klass = self._make_class()
        self.subject = self._make_subject_with_questions(self.klass, level=1, question_count=3)

    @patch('django_app.app_battle.engine._arm_question_timers')
    @patch('django_app.app_battle.tasks.maybe_inject_bot.apply_async')
    def test_two_random_queue_students_get_matched_into_one_room(self, mock_apply_async, mock_arm_timers):
        alice = self._make_student('+998900000001', self.klass)
        bob = self._make_student('+998900000002', self.klass)

        # Placement matches always go straight to a bot per the plan, so
        # bump both past placement to exercise the human-matching path.
        BattleRating.objects.create(student=alice, matches_played=10)
        BattleRating.objects.create(student=bob, matches_played=10)

        room_kwargs = dict(
            grade=self.klass, subjects=[self.subject],
            question_count=3, seconds_per_question=30,
        )

        room1, matched1 = matchmaking.find_or_create_room(alice, **room_kwargs)
        self.assertFalse(matched1)
        self.assertEqual(room1.status, BattleRoom.STATUS_WAITING)
        mock_apply_async.assert_called_once()

        room2, matched2 = matchmaking.find_or_create_room(bob, **room_kwargs)
        self.assertTrue(matched2)
        self.assertEqual(room2.id, room1.id, "second student must join the first student's waiting room")

        room1.refresh_from_db()
        self.assertEqual(room1.status, BattleRoom.STATUS_ACTIVE)
        self.assertEqual(room1.participants.count(), 2)
        self.assertEqual(BattleRoomQuestion.objects.filter(room=room1).count(), 3)
        mock_arm_timers.assert_called_once()

    def test_placement_student_never_enters_human_queue(self):
        alice = self._make_student('+998900000003', self.klass)
        BattleRating.objects.create(student=alice, matches_played=0)

        with patch('django_app.app_battle.tasks.maybe_inject_bot.apply_async') as mock_apply_async:
            room, matched = matchmaking.find_or_create_room(
                alice, grade=self.klass, subjects=[self.subject],
                question_count=3, seconds_per_question=30,
            )
        self.assertFalse(matched)
        mock_apply_async.assert_called_once()
        args, kwargs = mock_apply_async.call_args
        self.assertEqual(kwargs['countdown'], matchmaking.PLACEMENT_BOT_DELAY_SECONDS)

    @patch('django_app.app_battle.engine._arm_question_timers')
    @patch('django_app.app_battle.engine.send_event')
    def test_bot_injection_starts_the_match_and_never_leaks_is_bot(self, mock_send_event, mock_arm_timers):
        alice = self._make_student('+998900000004', self.klass)
        BattleRating.objects.create(student=alice, matches_played=0, elo=850)

        room = self._make_room(self.klass, [self.subject])
        matchmaking.create_participant_for_student(room, alice, is_creator=True)

        engine.maybe_inject_bot(room.id)

        room.refresh_from_db()
        self.assertEqual(room.status, BattleRoom.STATUS_ACTIVE)
        self.assertEqual(room.participants.count(), 2)

        from .serializers import serialize_room_snapshot
        snapshot = serialize_room_snapshot(room, alice)
        for participant_payload in snapshot['participants']:
            self.assertNotIn('is_bot', participant_payload)
            self.assertNotIn('bot_identity', participant_payload)


class EngineFullMatchTests(BattleFixtureMixin, TestCase):
    def setUp(self):
        self.klass = self._make_class('9')
        self.subject = self._make_subject_with_questions(self.klass, level=1, question_count=2)

    def test_full_match_updates_score_elo_rating_and_rewards_winner(self):
        alice = self._make_student('+998900000010', self.klass)
        bob = self._make_student('+998900000011', self.klass)
        BattleRating.objects.create(student=alice, matches_played=10, elo=1000)
        BattleRating.objects.create(student=bob, matches_played=10, elo=1000)

        room = self._make_room(self.klass, [self.subject], question_count=2)
        participant_a = matchmaking.create_participant_for_student(room, alice, is_creator=True)
        participant_b = matchmaking.create_participant_for_student(room, bob, is_creator=False)

        with patch('django_app.app_battle.engine._arm_question_timers'), \
                patch('django_app.app_battle.engine.send_event'):
            engine.start_match(room)

            for order in range(2):
                room_question = room.questions.get(order=order)
                correct_id = room_question.question.choices.get(is_correct=True).id
                wrong_id = room_question.question.choices.get(is_correct=False).id

                engine.record_answer(room.id, participant_a.id, order, {'choices': [correct_id]})
                engine.record_answer(room.id, participant_b.id, order, {'choices': [wrong_id]})

        room.refresh_from_db()
        self.assertEqual(room.status, BattleRoom.STATUS_FINISHED)

        participant_a.refresh_from_db()
        participant_b.refresh_from_db()
        self.assertEqual(participant_a.score, 2)
        self.assertEqual(participant_b.score, 0)
        self.assertGreater(participant_a.elo_after, participant_a.elo_before)
        self.assertLess(participant_b.elo_after, participant_b.elo_before)

        rating_a = BattleRating.objects.get(student=alice)
        rating_b = BattleRating.objects.get(student=bob)
        self.assertEqual(rating_a.wins, 1)
        self.assertEqual(rating_b.losses, 1)
        self.assertEqual(rating_a.matches_played, 11)

        from django_app.app_student.models import StudentScore
        alice_score = StudentScore.objects.get(student=alice)
        self.assertEqual(alice_score.score, engine.BATTLE_WIN_SCORE_REWARD)
        self.assertEqual(alice_score.coin, engine.BATTLE_WIN_COIN_REWARD)


class GradingTests(BattleFixtureMixin, TestCase):
    def test_choice_question_graded_correctly(self):
        klass = self._make_class('8')
        subject = self._make_subject_with_questions(klass, level=1, question_count=1)
        question = Question.objects.filter(topic__chapter__subject=subject).first()
        correct_id = question.choices.get(is_correct=True).id
        wrong_id = question.choices.get(is_correct=False).id

        from .grading import check_answer
        self.assertTrue(check_answer(question, {'choices': [correct_id]}))
        self.assertFalse(check_answer(question, {'choices': [wrong_id]}))
        self.assertFalse(check_answer(question, {'choices': []}))
