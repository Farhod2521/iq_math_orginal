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
        fields = ['id', 'letter', 'image'] + get_translation_fields('text')


class CompositeSubQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompositeSubQuestion
        fields = ['id', 'text1', 'text2'] + \
                 get_translation_fields('text1') + get_translation_fields('text2')


class CustomQuestionSerializer(serializers.ModelSerializer):
    choices = serializers.SerializerMethodField()
    sub_questions = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            'id', 'question_text', 'question_type', 'level',
            'question_text_uz', 'question_text_ru'
        ]

    def get_choices(self, obj):
        if obj.question_type != 'choice':
            return None

        choices_qs = obj.choices.all()
        return ChoiceSerializer(choices_qs, many=True).data if choices_qs else []

    def get_sub_questions(self, obj):
        if obj.question_type != 'composite':
            return None

        sub_qs = obj.sub_questions.all()
        if not sub_qs.exists():
            return None
        return CompositeSubQuestionSerializer(sub_qs, many=True).data

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.question_type == 'text':
            data['correct_text_answer'] = instance.correct_text_answer
        if instance.question_type == 'choice':
            data['choices'] = self.get_choices(instance)
        if instance.question_type == 'composite':
            sub_questions = self.get_sub_questions(instance)
            if sub_questions:
                data['sub_questions'] = sub_questions
            else:
                return None  # sub_question yo'q bo‘lsa umuman APIdan chiqmasin

        return data