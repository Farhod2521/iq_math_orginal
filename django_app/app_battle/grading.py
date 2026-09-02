"""Battle answer grading — thin wrapper reusing the exact checking logic
already used for diagnostics/tests in app_student, so battle results are
never graded by a second, possibly-diverging implementation.
"""

from django_app.app_teacher.models import Choice
from django_app.app_student.math_answer_check import advanced_math_check


def check_answer(question, raw_answer):
    """raw_answer shapes (mirrors the payloads app_student already accepts):
    - text:      {"answer_uz": "...", "answer_ru": "..."}
    - choice / image_choice: {"choices": [id, ...]}
    - composite: {"answers": ["...", ...]}
    """
    raw_answer = raw_answer or {}

    if question.question_type == 'text':
        answer_uz = (raw_answer.get('answer_uz') or '').strip()
        answer_ru = (raw_answer.get('answer_ru') or '').strip()
        if answer_uz:
            student_answer, correct_answer = answer_uz, (question.correct_text_answer_uz or '').strip()
        elif answer_ru:
            student_answer, correct_answer = answer_ru, (question.correct_text_answer_ru or '').strip()
        else:
            return False
        if not student_answer or not correct_answer:
            return False
        return advanced_math_check(student_answer, correct_answer)

    if question.question_type in ('choice', 'image_choice'):
        correct_choices = set(
            Choice.objects.filter(question=question, is_correct=True).values_list('id', flat=True)
        )
        selected_choices = set(raw_answer.get('choices') or [])
        return correct_choices == selected_choices

    if question.question_type == 'composite':
        correct_subs = list(question.sub_questions.order_by('id'))
        student_answers = raw_answer.get('answers') or []
        if len(student_answers) != len(correct_subs):
            return False
        for student_ans, sub_question in zip(student_answers, correct_subs):
            if not advanced_math_check(str(student_ans), str(sub_question.correct_answer)):
                return False
        return True

    return False
