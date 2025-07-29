from rest_framework import serializers
from .models import (
    Chapter, Topic, Question,Choice, CompositeSubQuestion, Group
    
)
from django_app.app_user.models import  Subject, Student

class SubjectSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="classes.name")  # Sinf nomini olish
    teachers = serializers.StringRelatedField(many=True)  # O‘qituvchi ismlarini olish

    class Meta:
        model = Subject
        fields = ["id", "name_uz", "name_ru", "class_name", "teachers",  "image_uz","image_ru"]  # Kerakli maydonlar
class SubjectRegisterSerilzier(serializers.ModelSerializer):
    class_name = serializers.CharField(source="classes.name")
    class_uz = serializers.SerializerMethodField()
    class_ru = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ["id", "name_uz", "name_ru", "class_name", "class_uz", "class_ru",  "image_uz","image_ru"]

    def get_class_uz(self, obj):
        return f"{obj.classes.name}-sinf {obj.name_uz}"

    def get_class_ru(self, obj):
        return f"{obj.classes.name}-класс {obj.name_ru}"
    

    
class MyChapterAddSerializer(serializers.ModelSerializer):
    class Meta:
        model =  Chapter
        fields = ["id", "name_uz", "name_ru", "subject"]

class MyTopicAddSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = [
            "id", "name_uz", "name_ru", "video_url_uz", "video_url_ru",
            "chapter", "content_uz", "content_ru", "question_count"
        ]

    def get_question_count(self, obj):
        return obj.questions.count()
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
        fields = ['question', 'letter', 'text_uz','text_ru', 'image', 'is_correct']
    
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
        fields = ["question", 'text1_uz','text1_ru', 'correct_answer', 'text2_uz', 'text2_ru']
class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)
    sub_questions = CompositeSubQuestionSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            'id', 'topic', 'question_text_uz', 'question_text_ru', 'question_type', 'level',
            "video_file_uz", "video_file_ru", "video_url_uz", "video_url_ru",
            'correct_text_answer_ru', 'correct_text_answer_uz', 'choices', 'sub_questions'
        ]

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        sub_questions_data = validated_data.pop('sub_questions', [])
        question = Question.objects.create(**validated_data)

        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)

        for sub_question_data in sub_questions_data:
            CompositeSubQuestion.objects.create(question=question, **sub_question_data)

        return question

    def update(self, instance, validated_data):
        choices_data = validated_data.pop('choices', None)
        sub_questions_data = validated_data.pop('sub_questions', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if choices_data is not None:
            instance.choices.all().delete()
            for choice in choices_data:
                Choice.objects.create(question=instance, **choice)

        if sub_questions_data is not None:
            instance.sub_questions.all().delete()
            for sub_q in sub_questions_data:
                CompositeSubQuestion.objects.create(question=instance, **sub_q)

        return instance


















class OpenAIChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'letter', 'text', 'image', 'is_correct']

class OpenAICompositeSubQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompositeSubQuestion
        fields = ['id', 'text1', 'correct_answer', 'text2']

class OpenAIQuestionSerializer(serializers.ModelSerializer):
    choices = OpenAIChoiceSerializer(many=True, read_only=True)
    sub_questions = OpenAICompositeSubQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            'id',
            'topic',
            'question_text_uz',
            'question_type',
            'level',
            'correct_text_answer_uz',
            'video_file_uz',
            'video_file_ru',
            'video_url_uz',
            'video_url_ru',
            'choices',
            'sub_questions',
        ]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name', 'teacher', 'students']
        extra_kwargs = {
            'teacher': {'read_only': True},  # teacher POST'da kiritilmaydi
            'students': {'required': False}
        }

class StudentSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_name.name', read_only=True)

    class Meta:
        model = Student
        fields = ['id', 'full_name', 'identification', 'class_name']

class GroupSerializer_DETAIL(serializers.ModelSerializer):
    students = StudentSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'teacher', 'students']
        extra_kwargs = {
            'teacher': {'read_only': True}
        }



class TeacherRewardSerializer(serializers.Serializer):
    teacher_id = serializers.IntegerField()
    student_id = serializers.IntegerField()
    reward_type = serializers.ChoiceField(choices=['score', 'coin', 'subscription_day'])
    amount = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(required=False, allow_blank=True)