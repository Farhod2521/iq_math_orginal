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
    

class CheckAnswersSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer = serializers.JSONField()

    def validate(self, data):
        question = Question.objects.get(id=data['question_id'])
        answer = data['answer']

        if question.question_type == "choice":
            correct_choices = Choice.objects.filter(question=question, is_correct=True)
            # Check if the answer contains only the correct choices
            correct_answers = {choice.letter for choice in correct_choices}
            provided_answers = {ans['letter'] for ans in answer if ans.get('is_correct')}
            if correct_answers != provided_answers:
                raise serializers.ValidationError("Savolga to‘g‘ri javoblar mos kelmayapti.")

        elif question.question_type == "text":
            # For 'text' type, check if the provided answer matches the correct text answer
            if question.correct_text_answer != answer:
                raise serializers.ValidationError("Savolga to‘g‘ri javob kiritilmadi.")

        elif question.question_type == "composite":
            # For composite type, check each sub-question's answer
            sub_questions = CompositeSubQuestion.objects.filter(question=question)
            for sub_question in sub_questions:
                correct_answer = sub_question.correct_answer
                provided_answer = next((ans['answer'] for ans in answer if ans['sub_question_id'] == sub_question.id), None)
                if provided_answer != correct_answer:
                    raise serializers.ValidationError("Bir nechta savollardan biri xato.")

        return data