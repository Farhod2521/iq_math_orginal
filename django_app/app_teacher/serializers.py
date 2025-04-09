from rest_framework import serializers
from .models import (
    Subject, Chapter, Topic, Question,
    QuestionImage
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

class MyQuestionImageAddSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=True)
    choice_letter = serializers.CharField(required=True)

    class Meta:
        model = QuestionImage
        fields = ["image", "choice_letter"]


class MyQuestionAddSerializer(serializers.ModelSerializer):
    images = MyQuestionImageAddSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ["question_text", "question_type", "correct_answer", "level", "choices", "images"]

    def create(self, validated_data):
        images_data = validated_data.pop("images", [])
        question = Question.objects.create(**validated_data)
        
        for image_data in images_data:
            QuestionImage.objects.create(question=question, **image_data)

        return question