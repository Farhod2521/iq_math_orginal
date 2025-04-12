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
    choices = ChoiceSerializer(many=True, read_only=True)
    sub_questions = CompositeSubQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            'id',
            'question_text_uz',
            'question_text_ru',
            'question_type',
            'level',
            'choices',
            'sub_questions',
        ] 

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.question_type == "text":
            # faqat kerakli fieldlarni qoldiramiz
            data.pop("choices", None)
            data.pop("sub_questions", None)
        elif instance.question_type == "choice":
            # choice type bo'lsa: is_correct, correct_text_answer, text ni olib tashlaymiz
            for choice in data.get("choices", []):
                choice.pop("is_correct", None)
                choice.pop("text", None)
            data.pop("correct_text_answer_uz", None)
            data.pop("correct_text_answer_ru", None)
            data.pop("sub_questions", None)
        elif instance.question_type == "composite":
            # agar composite bo‘lsa, lekin sub_questions bo‘sh bo‘lsa, umuman return qilmaymiz
            if not instance.sub_questions.exists():
                return None
            else:
                # sub_questions mavjud bo‘lsa ham correct_text_larni olib tashlaymiz

                data.pop("correct_text_answer_uz", None)
                data.pop("correct_text_answer_ru", None)
                data.pop("choices", None)
        return data
    
class CheckChoiceAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    choices = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )


class CheckTextAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer = serializers.CharField(max_length=1000)


class CheckCompositeAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answers = serializers.ListField(child=serializers.CharField(), allow_empty=False)


class CheckAnswersSerializer(serializers.Serializer):
    text_answers = CheckTextAnswerSerializer(many=True, required=False)
    choice_answers = CheckChoiceAnswerSerializer(many=True, required=False)
    composite_answers = CheckCompositeAnswerSerializer(many=True, required=False)