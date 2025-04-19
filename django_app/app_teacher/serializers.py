from rest_framework import serializers
from .models import (
    Chapter, Topic, Question,Choice, CompositeSubQuestion
    
)
from django_app.app_user.models import  Subject

class SubjectSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="classes.name")  # Sinf nomini olish
    teachers = serializers.StringRelatedField(many=True)  # O‘qituvchi ismlarini olish

    class Meta:
        model = Subject
        fields = ["id", "name", "class_name", "teachers",  "image"]  # Kerakli maydonlar
class SubjectRegisterSerilzier(serializers.ModelSerializer):
    class_name = serializers.CharField(source="classes.name")
    class_uz = serializers.SerializerMethodField()
    class_ru = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ["id", "name_uz", "name_ru", "class_name", "class_uz", "class_ru"]

    def get_class_uz(self, obj):
        return f"{obj.classes.name}-sinf {obj.name_uz}"

    def get_class_ru(self, obj):
        return f"{obj.classes.name}-класс {obj.name_ru}"
    

    
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
        required=False
    )
    image = serializers.ImageField(required=False, allow_null=True)
    letter = serializers.CharField(required=True)  # letter maydonini required=True qilib belgilang
    
    class Meta:
        model = Choice
        fields = ['question', 'letter', 'text', 'image', 'is_correct']
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.image:
            representation['image'] = instance.image.url
        return representation
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
        fields = ['id', 'topic', 'question_text', 'question_type', 'level',"video_file", "video_url", 'correct_text_answer', 'choices', 'sub_questions']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        sub_questions_data = validated_data.pop('sub_questions', [])
        question = Question.objects.create(**validated_data)

        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)

        for sub_question_data in sub_questions_data:
            CompositeSubQuestion.objects.create(question=question, **sub_question_data)

        return question