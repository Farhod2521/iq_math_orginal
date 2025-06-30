from rest_framework import serializers
from django_app.app_teacher.models import Chapter, Choice, CompositeSubQuestion, Question, Topic
from modeltranslation.utils import get_translation_fields

from django_app.app_user.models import  Subject, Student
from .models import TopicProgress, ChapterProgress, TopicHelpRequestIndependent
class SubjectSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="classes.name")
    class_uz = serializers.SerializerMethodField()
    class_ru = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()
    is_diagnost_open = serializers.SerializerMethodField()  # ✅ yangi field

    class Meta:
        model = Subject
        fields = [
            "id", "name_uz", "name_ru", "class_name", "class_uz", "class_ru",
            "image_uz", "image_ru", "is_open", "is_diagnost_open"
        ]

    def get_class_uz(self, obj):
        return f"{obj.classes.name}-sinf {obj.name_uz}"

    def get_class_ru(self, obj):
        return f"{obj.classes.name}-класс {obj.name_ru}"

    def get_is_open(self, obj):
        return self.context.get("is_open", False)

    def get_is_diagnost_open(self, obj):
        return self.context.get("is_diagnost_open", False)

    
class ChapterSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ['id', 'name_uz', 'name_ru', 'subject', 'progress']

    def get_progress(self, chapter):
        request = self.context.get('request')
        user = request.user

        # Agar foydalanuvchi o'qituvchi bo'lsa — progress doim 100%
        if hasattr(user, 'teacher_profile'):
            return 100.0

        # Student bo'lsa — ChapterProgress tekshiramiz
        try:
            student_instance = Student.objects.get(user=user)
            progress = ChapterProgress.objects.get(user=student_instance, chapter=chapter)
            return round(progress.progress_percentage, 2)
        except (ChapterProgress.DoesNotExist, Student.DoesNotExist):
            return 0.0

class TopicSerializer1(serializers.ModelSerializer):


    class Meta:
        model = Topic
        fields = ['id', 'name_uz', 'name_ru', 'chapter', "video_url_uz", "video_url_ru","content_uz", "content_ru", "is_locked"]


class TopicSerializer(serializers.ModelSerializer):
    is_open = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = [
            'id', 'name_uz', 'name_ru', 'chapter', 
            "video_url_uz", "video_url_ru", 
            "content_uz", "content_ru", 
            "is_locked", "is_open", "score"
        ]

    def get_score(self, obj):
        request = self.context.get('request')
        user = request.user

        if hasattr(user, 'teacher_profile'):
            return None

        try:
            student = Student.objects.get(user=user)
            progress = TopicProgress.objects.get(user=student, topic=obj)
            return round(progress.score, 1)
        except (Student.DoesNotExist, TopicProgress.DoesNotExist):
            return 0.0

    def get_is_locked(self, obj):
        request = self.context.get('request')
        user = request.user

        if hasattr(user, 'teacher_profile'):
            return False

        try:
            student = Student.objects.get(user=user)
        except Student.DoesNotExist:
            return True

        # Chapterdagi barcha topiclarni tartib bilan olamiz
        chapter_topics = Topic.objects.filter(chapter=obj.chapter).order_by('id')
        topic_ids = list(chapter_topics.values_list('id', flat=True))

        try:
            current_index = topic_ids.index(obj.id)
        except ValueError:
            return True  # Topic chapter ichida bo‘lmasa — qulflanadi

        # Agar birinchi topic bo‘lsa — doim ochiq
        if current_index == 0:
            return False

        # Oldingi topicni topamiz
        prev_topic_id = topic_ids[current_index - 1]
        try:
            prev_topic = Topic.objects.get(id=prev_topic_id)
            prev_progress = TopicProgress.objects.get(user=student, topic=prev_topic)
            if prev_progress.score >= 80:
                return False  # oldingi topic 80%+ bo‘lsa — bu topic ochiladi
        except TopicProgress.DoesNotExist:
            pass

        return True  # Aks holda — qulflanadi

    def get_is_open(self, obj):
        return not self.get_is_locked(obj)
class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'letter', 'image'] + get_translation_fields('text')


class CompositeSubQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompositeSubQuestion
        fields = ['id', 'text1_uz','text1_ru', 'text2_uz', 'text2_ru']


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

                # Bu yerda "undefined" ni "" ga o'zgartiramiz
                for sub_question in data.get("sub_questions", []):
                    if sub_question.get("text2_uz") == "undefined":
                        sub_question["text2_uz"] = ""
                    if sub_question.get("text2_ru") == "undefined":
                        sub_question["text2_ru"] = ""

        return data

    
class CheckChoiceAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    choices = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )


class CheckTextAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answer_uz = serializers.CharField(max_length=1000, required=False)
    answer_ru = serializers.CharField(max_length=1000, required=False)


class CheckCompositeAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    answers = serializers.ListField(child=serializers.CharField(), allow_empty=False)


class CheckAnswersSerializer(serializers.Serializer):
    text_answers = CheckTextAnswerSerializer(many=True, required=False)
    choice_answers = CheckChoiceAnswerSerializer(many=True, required=False)
    composite_answers = CheckCompositeAnswerSerializer(many=True, required=False)


class TopicHelpRequestIndependentSerializer(serializers.ModelSerializer):
    info = serializers.JSONField(write_only=True)
    question = serializers.JSONField(write_only=True)
    result = serializers.JSONField(write_only=True)

    class Meta:
        model = TopicHelpRequestIndependent
        fields = ['id', 'info', 'question', 'result', 'level']

    def to_internal_value(self, data):
        # override qilamiz required fieldlar validatsiyasini o‘chirib qo‘yish uchun
        ret = super().to_internal_value(data)
        ret['info'] = data.get('info')
        ret['question'] = data.get('question')
        ret['result'] = data.get('result')
        return ret

    def create(self, validated_data):
        request = self.context['request']
        student = request.user.student_profile

        info = validated_data.pop('info')
        question_json = validated_data.pop('question')
        result_json = validated_data.pop('result')

        # Extracting subject/chapter/topic from info
        subject_id = info['subject']['id']
        chapter_id = info['chapter']['id']
        topic_id = info['topic']['id']

        subject = Subject.objects.get(id=subject_id)
        chapter = Chapter.objects.get(id=chapter_id)
        topic = Topic.objects.get(id=topic_id)

        instance = TopicHelpRequestIndependent.objects.create(
            student=student,
            subject=subject,
            level=validated_data.get('level', 1),
            question_json=question_json,
            result_json=result_json,
        )
        instance.chapters.set([chapter])
        instance.topics.set([topic])
        return instance

class TopicHelpRequestIndependentSerializer(serializers.ModelSerializer):
    commit_uz = serializers.CharField(required=False, allow_blank=True)
    commit_ru = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = TopicHelpRequestIndependent
        fields = [
            'id', 'student', 'subject', 'chapters', 'topics', 'level',
            'question_json', 'result_json',
            'teacher', 'commit_uz', 'commit_ru', 'reviewed_at', 'created_at'
        ]
        read_only_fields = ['student', 'created_at', 'teacher', 'reviewed_at']