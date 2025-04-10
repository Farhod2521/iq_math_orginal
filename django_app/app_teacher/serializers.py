from rest_framework import serializers
from .models import (
    Subject, Chapter, Topic, Question,Choice, CompositeSubQuestion
    
)


class SubjectSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="classes.name")  # Sinf nomini olish
    teachers = serializers.StringRelatedField(many=True)  # O‘qituvchi ismlarini olish

    class Meta:
        model = Subject
        fields = ["id", "name", "class_name", "teachers",  "image"]  # Kerakli maydonlar



class MyChapterAddSerializer(serializers.ModelSerializer):
    class Meta:
        model =  Chapter
        fields = "__all__"

class MyTopicAddSerializer(serializers.ModelSerializer):
    class Meta:
        model =  Topic
        fields = "__all__"


class ChoiceSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.all(),
        write_only=True,
        required=False  # required=False dan required=True ga o'zgartirildi
    )

    class Meta:
        model = Choice
        fields = ['question', 'letter', 'text', 'image', 'is_correct']

class CompositeSubQuestionSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(
        queryset=Question.objects.all(),
        write_only=True,
        required=False  # required=False dan required=True ga o'zgartirildi
    )
    
    class Meta:
        model = CompositeSubQuestion
        fields = ["question", 'text1', 'correct_answer', 'text2']
class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)
    sub_questions = CompositeSubQuestionSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['id', 'topic', 'question_text', 'question_type', 'level', 'correct_text_answer', 'choices', 'sub_questions']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        sub_questions_data = validated_data.pop('sub_questions', [])
        question = Question.objects.create(**validated_data)

        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)

        for sub_question_data in sub_questions_data:
            CompositeSubQuestion.objects.create(question=question, **sub_question_data)

        return question