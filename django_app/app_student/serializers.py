from rest_framework import serializers
from django_app.app_teacher.models import Subject, Chapter, Choice, CompositeSubQuestion, Question
from modeltranslation.utils import get_translation_fields
class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'teachers', "image"]




class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'letter', 'text', 'image', 'is_correct'] + get_translation_fields('text')

class CompositeSubQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompositeSubQuestion
        fields = ['id', 'text1', 'text2', 'correct_answer'] + \
                 get_translation_fields('text1') + get_translation_fields('text2') + get_translation_fields('correct_answer')

class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    sub_questions = CompositeSubQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'question_text', 'question_type', 'level', 'correct_text_answer',
            'choices', 'sub_questions'
        ] + get_translation_fields('question_text') + get_translation_fields('correct_text_answer')