from rest_framework import serializers
from django_app.app_teacher.models import Chapter, Choice, CompositeSubQuestion, Question, Topic
from modeltranslation.utils import get_translation_fields

from django_app.app_user.models import  Subject, Student
from .models import TopicProgress
class SubjectSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="classes.name")
    class_uz = serializers.SerializerMethodField()
    class_ru = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ["id", "name_uz", "name_ru", "class_name", "class_uz", "class_ru", "image_uz", "image_ru"]

    def get_class_uz(self, obj):
        return f"{obj.classes.name}-sinf {obj.name_uz}"

    def get_class_ru(self, obj):
        return f"{obj.classes.name}-класс {obj.name_ru}"
    
class ChapterSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    class Meta:
        model = Chapter
        fields = ['id', 'name_uz', 'name_ru','subject']
    def get_progress(self, chapter):
        request = self.context.get('request')
        user = request.user

        from .models import ChapterProgress  # model nomi mos bo‘lsin

        try:
            progress = ChapterProgress.objects.get(user=user, chapter=chapter)
            return round(progress.progress_percentage, 2)
        except ChapterProgress.DoesNotExist:
            return 0.0




class TopicSerializer(serializers.ModelSerializer):
    is_open = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = ['id', 'name_uz', 'name_ru', 'chapter', "video_url", "content_uz", "content_ru", "is_locked", "is_open"]

    def get_is_open(self, obj):
        request = self.context.get('request')
        user = request.user

        # Agar mavzu qulflangan bo‘lsa, hech kimga ochilmaydi
        if obj.is_locked:
            return False

        # Agar admin tomonidan ochilgan bo'lsa, unda is_open True bo'lishi kerak
        if not obj.is_locked:
            return True

        # Foydalanuvchini Student obyekti sifatida olish
        try:
            student_instance = Student.objects.get(user=user)  # Foydalanuvchi orqali Student olish
            progress = TopicProgress.objects.get(user=student_instance, topic=obj)
            return progress.is_unlocked
        except (TopicProgress.DoesNotExist, Student.DoesNotExist):
            return False
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
            data.pop("choices", None)
            data.pop("sub_questions", None)

        elif instance.question_type == "choice":
            # To‘g‘ri javoblar soniga qarab question_category ni qo‘shamiz
            correct_count = instance.choices.filter(is_correct=True).count()
            data["question_category"] = "checkbox" if correct_count > 1 else "radio_button"

            for choice in data.get("choices", []):
                choice.pop("is_correct", None)
                choice.pop("text", None)

            data.pop("correct_text_answer_uz", None)
            data.pop("correct_text_answer_ru", None)
            data.pop("sub_questions", None)

        elif instance.question_type == "composite":
            if not instance.sub_questions.exists():
                return None
            else:
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