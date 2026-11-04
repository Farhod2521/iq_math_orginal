# -*- coding: utf-8 -*-
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from django_app.app_payments.models import Subscription
from django_app.app_student.models import StudentScore, StudentScoreLog
from django_app.app_teacher.models import Chapter, Question, Topic
from django_app.app_user.models import Class, Student, StudentLoginHistory, Subject, Subject_Category, User

from . import services
from .models import (
    LigaAnswer, LigaAttempt, LigaChoice, LigaParticipant, LigaPointLog, LigaQuestion, LigaSeason, LigaTest, LigaWinner,
)


class LigaFixtureMixin:
    def setUp(self):
        self.klass = Class.objects.create(name='8')
        category = Subject_Category.objects.create(name='Matematika')
        self.subject = Subject.objects.create(name='Algebra', classes=self.klass, category=category)
        self.season = LigaSeason.objects.create(number=1, weeks_count=2, is_published=True)
        self.test = self._test(week=1)
        self.q1 = self._question('2+2')
        self.q2 = self._question('3+3')
        self.student = self._student('+998900000001')
        self.participant = services.join_season(self.season, self.student)

    def _test(self, week, klass=None, **extra):
        now = timezone.now()
        defaults = {
            'start_at': now - timedelta(minutes=5), 'end_at': now + timedelta(hours=2),
            'duration_minutes': 30, 'is_published': True,
        }
        defaults.update(extra)
        return LigaTest.objects.create(season=self.season, grade=klass or self.klass, week_number=week, **defaults)

    def _question(self, text, score=1, test=None):
        question = LigaQuestion.objects.create(
            test=test or self.test, subject=self.subject, question_text=text, score=score,
        )
        LigaChoice.objects.create(question=question, letter='A', text='ha', is_correct=True)
        LigaChoice.objects.create(question=question, letter='B', text="yo'q", is_correct=False)
        return question

    def _student(self, phone, name='Azizbek Olimov Akmalovich', subject=None, paid=True):
        user = User.objects.create_user(phone=phone, password='pass12345', role='student')
        student = Student.objects.create(user=user, full_name=name, class_name=subject or self.subject)
        Subscription.objects.create(student=student, end_date=timezone.now() + timedelta(days=30), is_paid=paid)
        return student

    def _client(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def _correct(self, question):
        return question.choices.get(is_correct=True)

    def _wrong(self, question):
        return question.choices.get(is_correct=False)

    def _points(self, participant=None):
        return LigaParticipant.objects.get(pk=(participant or self.participant).pk).points


class JoinTests(LigaFixtureMixin, TestCase):
    def test_unpaid_student_cannot_join(self):
        student = self._student('+998900000002', paid=False)
        response = self._client(student.user).post(f'/api/v1/liga/seasons/{self.season.id}/join/')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(LigaParticipant.objects.filter(student=student).exists())

    def test_expired_subscription_cannot_join(self):
        student = self._student('+998900000002')
        Subscription.objects.filter(student=student).update(end_date=timezone.now() - timedelta(days=1))
        response = self._client(student.user).post(f'/api/v1/liga/seasons/{self.season.id}/join/')
        self.assertEqual(response.status_code, 400)

    def test_join_stores_registered_grade_and_gives_daily_point(self):
        student = self._student('+998900000002')
        response = self._client(student.user).post(f'/api/v1/liga/seasons/{self.season.id}/join/')
        self.assertEqual(response.status_code, 201)
        participant = LigaParticipant.objects.get(student=student)
        self.assertEqual(participant.grade, self.klass)
        self.assertEqual(participant.points, 1)

    def test_student_sees_only_own_grade_tests(self):
        other = Class.objects.create(name='9')
        self._test(week=1, klass=other)
        response = self._client(self.student.user).get('/api/v1/liga/current/')
        self.assertEqual([row['id'] for row in response.data['tests']], [self.test.id])
        self.assertTrue(response.data['joined'])


class PointsTests(LigaFixtureMixin, TestCase):
    def test_daily_login_counts_once_per_day(self):
        StudentLoginHistory.objects.create(student=self.student)
        StudentLoginHistory.objects.create(student=self.student)
        self.assertEqual(self._points(), 1)

    def test_subject_work_adds_points(self):
        category = Subject_Category.objects.create(name='F')
        subject = Subject.objects.create(name='Fan', classes=self.klass, category=category)
        topic = Topic.objects.create(name='T', chapter=Chapter.objects.create(name='C', subject=subject))
        question = Question.objects.create(topic=topic, question_text='1', question_type='choice', level=1)
        score = StudentScore.objects.create(student=self.student)
        StudentScoreLog.objects.create(student_score=score, question=question)
        self.assertEqual(self._points(), 1)

    def test_not_joined_student_gets_no_points(self):
        student = self._student('+998900000002')
        StudentLoginHistory.objects.create(student=student)
        self.assertFalse(LigaPointLog.objects.filter(participant__student=student).exists())

    def test_test_score_is_added_once(self):
        attempt = services.start_attempt(self.test, self.student)
        services.save_answer(attempt.id, self.q1.id, self._correct(self.q1).id)
        services.finish_attempt(attempt.id)
        services.finish_attempt(attempt.id)
        self.assertEqual(self._points(), 1)


class StartTests(LigaFixtureMixin, TestCase):
    def _start(self, student=None):
        return self._client((student or self.student).user).post(f'/api/v1/liga/tests/{self.test.id}/start/')

    def test_cannot_start_before_start_time(self):
        LigaTest.objects.filter(pk=self.test.pk).update(start_at=timezone.now() + timedelta(hours=1))
        self.assertEqual(self._start().status_code, 400)
        self.assertFalse(LigaAttempt.objects.exists())

    def test_must_join_first(self):
        self.assertEqual(self._start(self._student('+998900000002')).status_code, 400)

    def test_other_grade_is_rejected(self):
        subject = Subject.objects.create(name='Geometriya', classes=Class.objects.create(name='9'))
        student = self._student('+998900000002', subject=subject)
        services.join_season(self.season, student)
        self.assertEqual(self._start(student).status_code, 400)

    def test_subscription_ended_after_join_is_rejected(self):
        Subscription.objects.filter(student=self.student).update(end_date=timezone.now() - timedelta(days=1))
        self.assertEqual(self._start().status_code, 400)

    def test_student_gets_only_question_count_from_pool(self):
        for index in range(30):
            self._question(f'q{index}')
        LigaTest.objects.filter(pk=self.test.pk).update(question_count=25)
        response = self._start()
        self.assertEqual(len(response.data['questions']), 25)
        self.assertEqual(response.data['total_questions'], 25)

    def test_reopening_continues_same_questions_and_timer(self):
        first = self._start().data
        second = self._start().data
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(first['deadline_at'], second['deadline_at'])
        self.assertEqual([q['id'] for q in first['questions']], [q['id'] for q in second['questions']])
        self.assertEqual(LigaAttempt.objects.count(), 1)

    def test_finished_test_cannot_be_retaken(self):
        attempt = services.start_attempt(self.test, self.student)
        services.finish_attempt(attempt.id)
        response = self._start()
        self.assertNotIn('questions', response.data)
        self.assertEqual(LigaAttempt.objects.count(), 1)

    def test_late_student_deadline_capped_by_window(self):
        LigaTest.objects.filter(pk=self.test.pk).update(end_at=timezone.now() + timedelta(minutes=10))
        self.test.refresh_from_db()
        attempt = services.start_attempt(self.test, self.student)
        self.assertEqual(attempt.deadline_at, self.test.end_at)

    def test_payload_never_contains_correct_answers(self):
        response = self._start()
        for question in response.data['questions']:
            self.assertNotIn('correct_text_answer', question)
            for choice in question['choices']:
                self.assertNotIn('is_correct', choice)


class AnswerTests(LigaFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.attempt = services.start_attempt(self.test, self.student)
        self.client_api = self._client(self.student.user)
        self.url = f'/api/v1/liga/attempts/{self.attempt.id}'

    def test_saved_answers_come_back_on_reopen(self):
        choice = self._correct(self.q1)
        self.client_api.post(f'{self.url}/answer/', {'question': self.q1.id, 'choice': choice.id}, format='json')
        data = self.client_api.get(f'{self.url}/').data
        self.assertEqual(data['answers'], [{'question': self.q1.id, 'choice': choice.id, 'text_answer': None}])
        self.assertGreater(data['remaining_seconds'], 0)

    def test_unanswered_questions_count_as_wrong(self):
        self.client_api.post(f'{self.url}/answer/', {'question': self.q1.id, 'choice': self._correct(self.q1).id}, format='json')
        data = self.client_api.post(f'{self.url}/finish/').data
        self.assertEqual(data['correct_count'], 1)
        self.assertEqual(data['wrong_count'], 1)
        self.assertEqual(data['score'], 1)
        self.assertEqual(data['max_score'], 2)

    def test_answer_can_be_changed(self):
        self.client_api.post(f'{self.url}/answer/', {'question': self.q1.id, 'choice': self._wrong(self.q1).id}, format='json')
        self.client_api.post(f'{self.url}/answer/', {'question': self.q1.id, 'choice': self._correct(self.q1).id}, format='json')
        self.assertEqual(LigaAnswer.objects.count(), 1)
        self.assertTrue(LigaAnswer.objects.get().is_correct)

    def test_question_outside_generated_set_is_rejected(self):
        extra = self._question('boshqa')
        response = self.client_api.post(
            f'{self.url}/answer/', {'question': extra.id, 'choice': self._correct(extra).id}, format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_choice_of_another_question_is_rejected(self):
        response = self.client_api.post(
            f'{self.url}/answer/', {'question': self.q1.id, 'choice': self._correct(self.q2).id}, format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_text_question_uses_math_check(self):
        question = LigaQuestion.objects.create(
            test=self.test, subject=self.subject, question_text='1/2', question_type='text', correct_text_answer='0.5',
        )
        LigaAttempt.objects.filter(pk=self.attempt.pk).update(question_order=[self.q1.id, self.q2.id, question.id])
        self.client_api.post(f'{self.url}/answer/', {'question': question.id, 'text_answer': '0,5'}, format='json')
        self.assertTrue(LigaAnswer.objects.get(question=question).is_correct)

    def test_time_out_closes_with_marked_answers_only(self):
        services.save_answer(self.attempt.id, self.q1.id, self._correct(self.q1).id)
        LigaAttempt.objects.filter(pk=self.attempt.pk).update(deadline_at=timezone.now() - timedelta(seconds=1))
        response = self.client_api.post(
            f'{self.url}/answer/', {'question': self.q2.id, 'choice': self._correct(self.q2).id}, format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.status, LigaAttempt.STATUS_EXPIRED)
        self.assertEqual(self.attempt.correct_count, 1)
        self.assertEqual(self._points(), 1)

    def test_answer_after_finish_is_rejected(self):
        self.client_api.post(f'{self.url}/finish/')
        response = self.client_api.post(
            f'{self.url}/answer/', {'question': self.q1.id, 'choice': self._correct(self.q1).id}, format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_other_student_cannot_open_attempt(self):
        other = self._student('+998900000003')
        self.assertEqual(self._client(other.user).get(f'{self.url}/').status_code, 404)

    def test_celery_task_closes_abandoned_attempts(self):
        LigaAttempt.objects.filter(pk=self.attempt.pk).update(deadline_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(services.finalize_expired(), 1)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.status, LigaAttempt.STATUS_EXPIRED)


class SeasonCloseTests(LigaFixtureMixin, TestCase):
    def _player(self, phone, points, name='Ali Valiyev Karimovich'):
        participant = services.join_season(self.season, self._student(phone, name=name))
        LigaParticipant.objects.filter(pk=participant.pk).update(points=points)
        return participant

    def _end_all_tests(self):
        past = timezone.now() - timedelta(minutes=1)
        self.season.tests.update(start_at=past - timedelta(hours=1), end_at=past)

    def test_not_closed_until_last_week_test_ended(self):
        self._end_all_tests()
        self.assertEqual(services.close_finished_seasons(), 0)  # 2 haftadan faqat 1-hafta bor
        self._test(week=2)
        self.assertEqual(services.close_finished_seasons(), 0)  # 2-hafta hali davom etmoqda
        self._end_all_tests()
        self.assertEqual(services.close_finished_seasons(), 1)
        self.season.refresh_from_db()
        self.assertTrue(self.season.is_closed)

    def test_close_keeps_three_winners_per_grade_and_resets_points(self):
        LigaParticipant.objects.filter(pk=self.participant.pk).update(points=5)
        first = self._player('+998900000011', 40)
        second = self._player('+998900000012', 30)
        third = self._player('+998900000013', 20)
        services.close_season(self.season.id)

        winners = list(LigaWinner.objects.filter(season=self.season).order_by('place'))
        self.assertEqual([w.student_id for w in winners], [first.student_id, second.student_id, third.student_id])
        self.assertEqual([w.points for w in winners], [40, 30, 20])
        self.assertEqual([w.prize_uz for w in winners], ['Planshet', 'Telefon', 'Quloqchin'])
        self.assertEqual(sum(LigaParticipant.objects.values_list('points', flat=True)), 0)

    def test_close_is_idempotent_and_blocks_new_points(self):
        self._player('+998900000011', 40)
        services.close_season(self.season.id)
        services.close_season(self.season.id)
        self.assertEqual(LigaWinner.objects.count(), 1)
        StudentLoginHistory.objects.create(student=self.student)
        self.assertEqual(self._points(), 0)

    def test_zero_point_students_do_not_win(self):
        services.close_season(self.season.id)
        self.assertFalse(LigaWinner.objects.exists())

    def test_close_finalizes_open_attempts_first(self):
        attempt = services.start_attempt(self.test, self.student)
        services.save_answer(attempt.id, self.q1.id, self._correct(self.q1).id)
        LigaAttempt.objects.filter(pk=attempt.pk).update(deadline_at=timezone.now() - timedelta(seconds=1))
        services.close_season(self.season.id)
        self.assertEqual(LigaWinner.objects.get().points, 1)

    def test_public_winners_hide_full_name(self):
        self._player('+998900000011', 40)
        services.close_season(self.season.id)
        response = APIClient().get('/api/v1/liga/winners/')
        self.assertEqual(response.data[0]['winners'][0]['full_name'], 'Ali V.')
        self.assertNotIn('phone', response.data[0]['winners'][0])

    def test_live_top_uses_public_names_and_shows_my_rank(self):
        self._player('+998900000011', 40)
        data = self._client(self.student.user).get('/api/v1/liga/current/').data
        self.assertEqual(data['top'][0]['full_name'], 'Ali V.')
        self.assertEqual(data['rank'], 2)


class AdminApiTests(LigaFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.mentor = self._client(User.objects.create_user(phone='+998900000099', password='pass12345', role='teacher'))

    def _payload(self, **extra):
        data = {
            'test': self.test.id, 'subject': self.subject.id, 'question_text_uz': '5+5', 'question_type': 'choice',
            'choices': [
                {'letter': 'A', 'text_uz': '10', 'is_correct': True},
                {'letter': 'B', 'text_uz': '11', 'is_correct': False},
            ],
        }
        data.update(extra)
        return data

    def test_student_has_no_admin_access(self):
        self.assertEqual(self._client(self.student.user).get('/api/v1/liga/admin/tests/').status_code, 403)

    def test_create_question_with_choices(self):
        response = self.mentor.post('/api/v1/liga/admin/questions/', self._payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(LigaQuestion.objects.get(pk=response.data['id']).choices.count(), 2)

    def test_question_needs_exactly_one_correct_choice(self):
        choices = [{'letter': 'A', 'text_uz': '1', 'is_correct': True}, {'letter': 'B', 'text_uz': '2', 'is_correct': True}]
        response = self.mentor.post('/api/v1/liga/admin/questions/', self._payload(choices=choices), format='json')
        self.assertEqual(response.status_code, 400)

    def test_subject_must_match_test_grade(self):
        other = Subject.objects.create(name='Fizika', classes=Class.objects.create(name='9'))
        response = self.mentor.post('/api/v1/liga/admin/questions/', self._payload(subject=other.id), format='json')
        self.assertEqual(response.status_code, 400)

    def test_questions_locked_after_first_attempt(self):
        services.start_attempt(self.test, self.student)
        create = self.mentor.post('/api/v1/liga/admin/questions/', self._payload(), format='json')
        delete = self.mentor.delete(f'/api/v1/liga/admin/questions/{self.q1.id}/')
        self.assertEqual(create.status_code, 400)
        self.assertEqual(delete.status_code, 400)

    def test_cannot_publish_empty_test(self):
        now = timezone.now()
        response = self.mentor.post('/api/v1/liga/admin/tests/', {
            'season': self.season.id, 'grade': Class.objects.create(name='9').id, 'week_number': 1,
            'duration_minutes': 30, 'is_published': True,
            'start_at': now.isoformat(), 'end_at': (now + timedelta(hours=1)).isoformat(),
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_bulk_create_for_several_grades(self):
        now = timezone.now()
        grades = [Class.objects.create(name='9').id, Class.objects.create(name='10').id]
        body = {
            'season': self.season.id, 'grades': grades, 'week_number': 2, 'duration_minutes': 40,
            'start_at': now.isoformat(), 'end_at': (now + timedelta(hours=2)).isoformat(),
        }
        response = self.mentor.post('/api/v1/liga/admin/tests/bulk-create/', body, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(LigaTest.objects.filter(week_number=2).count(), 2)
        repeat = self.mentor.post('/api/v1/liga/admin/tests/bulk-create/', body, format='json')
        self.assertEqual(repeat.status_code, 400)

    def test_participants_list_and_excel(self):
        attempt = services.start_attempt(self.test, self.student)
        services.save_answer(attempt.id, self.q1.id, self._correct(self.q1).id)
        services.finish_attempt(attempt.id)
        url = f'/api/v1/liga/admin/tests/{self.test.id}/participants/'
        row = self.mentor.get(url).data['results'][0]
        self.assertEqual(row['full_name'], 'Azizbek Olimov Akmalovich')
        self.assertEqual(row['rank'], 1)
        self.assertEqual(row['correct_count'], 1)
        self.assertIsNotNone(row['duration_seconds'])
        self.assertIn('spreadsheetml', self.mentor.get(url, {'export': 'xlsx'})['Content-Type'])

    def test_dashboard_and_standings(self):
        attempt = services.start_attempt(self.test, self.student)
        services.save_answer(attempt.id, self.q1.id, self._correct(self.q1).id)
        services.finish_attempt(attempt.id)
        StudentLoginHistory.objects.create(student=self.student)

        data = self.mentor.get(f'/api/v1/liga/admin/seasons/{self.season.id}/dashboard/').data
        self.assertEqual(data['cards']['participants'], 1)
        self.assertEqual(data['cards']['attempts'], 1)
        self.assertEqual(data['points_by_source'], {'daily': 1, 'subject': 0, 'test': 1})
        grade = next(row for row in data['grades'] if row['grade'] == '8')
        self.assertEqual(grade['leader_points'], 2)
        self.assertEqual(data['weeks'][0]['attempts'], 1)

        rows = self.mentor.get(f'/api/v1/liga/admin/seasons/{self.season.id}/standings/').data['results']
        self.assertEqual(rows[0]['full_name'], 'Azizbek Olimov Akmalovich')
        self.assertEqual(rows[0]['tests_taken'], 1)

    def test_mentor_can_disqualify_winner(self):
        LigaParticipant.objects.filter(pk=self.participant.pk).update(points=5)
        self.mentor.post(f'/api/v1/liga/admin/seasons/{self.season.id}/close/')
        winner = LigaWinner.objects.get()
        response = self.mentor.patch(
            f'/api/v1/liga/admin/winners/{winner.id}/',
            {'is_disqualified': True, 'disqualify_reason': "Sinf noto'g'ri", 'points': 999}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        winner.refresh_from_db()
        self.assertTrue(winner.is_disqualified)
        self.assertEqual(winner.points, 5)
