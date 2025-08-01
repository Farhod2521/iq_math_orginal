from rest_framework import serializers
from django_app.app_teacher.models import Chapter, Choice, CompositeSubQuestion, Question, Topic
from modeltranslation.utils import get_translation_fields

from django_app.app_user.models import  Subject, Student, StudentLoginHistory
from .models import TopicProgress, ChapterProgress, TopicHelpRequestIndependent, StudentReferral
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

        if user.role in ['teacher', 'admin']:
            return None  # 👨‍🏫 Admin va teacher uchun score ko‘rsatilmaydi

        try:
            student = Student.objects.get(user=user)
            progress = TopicProgress.objects.get(user=student, topic=obj)
            return round(progress.score, 1)
        except (Student.DoesNotExist, TopicProgress.DoesNotExist):
            return 0.0

    def get_is_locked(self, obj):
        request = self.context.get('request')
        user = request.user

        if user.role in ['teacher', 'admin']:
            return False  # 👨‍🏫 Admin va teacher uchun doim ochiq

        try:
            student = Student.objects.get(user=user)
        except Student.DoesNotExist:
            return True

        # 1. Agar bu mavzu allaqachon ishlangan bo‘lsa → ochiq
        if TopicProgress.objects.filter(user=student, topic=obj).exists():
            return False

        # 2. Chapterdagi topiclar
        chapter_topics = Topic.objects.filter(chapter=obj.chapter).order_by('order')
        topic_ids = list(chapter_topics.values_list('id', flat=True))

        try:
            current_index = topic_ids.index(obj.id)
        except ValueError:
            return True

        # ✅ 3. Agar bu chapter ichidagi BIRINCHI mavzu bo‘lsa → har doim ochiq bo‘lsin
        if current_index == 0:
            return False  # ❗ istisno: chapter ichida birinchi mavzu doim ochiq

        # 4. Aks holda — oldingi topicni tekshiramiz
        prev_topic_id = topic_ids[current_index - 1]
        try:
            prev_topic = Topic.objects.get(id=prev_topic_id)
            prev_progress = TopicProgress.objects.get(user=student, topic=prev_topic)
            return not (prev_progress.score >= 80)
        except TopicProgress.DoesNotExist:
            return True

    def get_is_open(self, obj):
        request = self.context.get('request')
        user = request.user

        if user.role in ['teacher', 'admin']:
            return True  # 👨‍🏫 Admin va teacher uchun doim ochiq

        try:
            student = Student.objects.get(user=user)
        except Student.DoesNotExist:
            return False

        # ✅ Agar mavzu allaqachon ishlangan bo‘lsa
        if TopicProgress.objects.filter(user=student, topic=obj).exists():
            return True

        # ✅ Fanning (subject) eng birinchi bobini topamiz
        first_chapter = Chapter.objects.filter(subject=obj.chapter.subject).order_by('order').first()
        if not first_chapter:
            return False  # Bob yo‘q bo‘lsa, yopiq

        # ✅ Shu bobdagi eng birinchi mavzuni topamiz
        first_topic = Topic.objects.filter(chapter=first_chapter).order_by('order').first()
        if not first_topic:
            return False  # Mavzular yo‘q bo‘lsa, yopiq

        # ✅ Agar hozirgi mavzu aynan fanning birinchi bobidagi birinchi mavzu bo‘lsa
        if obj.id == first_topic.id:
            return True

        return False  # Boshqa holatlarda — yopiq


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
                    if sub_question.get("text2_uz") in [None, "undefined"]:
                        sub_question["text2_uz"] = ""
                    if sub_question.get("text2_ru") in [None, "undefined"]:
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



from django.utils.html import strip_tags

class TopicHelpRequestIndependentSerializer(serializers.ModelSerializer):
    info = serializers.JSONField(write_only=True)
    question = serializers.JSONField(write_only=True)
    result = serializers.JSONField(write_only=True)

    class Meta:
        model = TopicHelpRequestIndependent
        exclude = [
            'subject', 'chapters', 'topics', 'question_json', 'result_json',
            'student', 'commit', 'reviewed_at', 'level'
        ]

    def create(self, validated_data):
        request = self.context['request']
        student = request.user.student_profile

        info = validated_data.pop('info')
        questions = validated_data.pop('question')
        result_json = validated_data.pop('result')

        subject = Subject.objects.get(id=info['subject']['id'])
        chapter = Chapter.objects.get(id=info['chapter']['id'])
        topic = Topic.objects.get(id=info['topic']['id'])

        # 🧠 SYSTEM JAVOBLARNI QO‘SHISH + SAVOL TURINI QO‘SHISH
        for q in questions:
            question_id = q.get("question_id")
            try:
                question_obj = Question.objects.get(id=question_id)
            except Question.DoesNotExist:
                q["system_response"] = None
                q["question_type"] = None
                continue

            # ➕ Savol turini yozamiz
            q["question_type"] = question_obj.question_type

            if question_obj.question_type == "text":
                q["system_response"] = strip_tags(question_obj.correct_text_answer or "")
            elif question_obj.question_type == "composite":
                q["system_response"] = [
                    sub.correct_answer for sub in question_obj.sub_questions.all()
                ]
            elif question_obj.question_type in ["choice", "image_choice"]:
                q["system_response"] = [
                    choice.letter for choice in question_obj.choices.filter(is_correct=True)
                ]
            else:
                q["system_response"] = None

        # 🔗 Bazaga yozish
        instance = TopicHelpRequestIndependent.objects.create(
            student=student,
            subject=subject,
            level=validated_data.get('level', 1),
            question_json={"question": questions, "result": result_json, "info": info},
            result_json=result_json
        )
        instance.chapters.set([chapter])
        instance.topics.set([topic])
        return instance



class ReferredStudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='referred.full_name')


    class Meta:
        model = StudentReferral
        fields = ['full_name',  'referred_at']


from django.utils.timezone import localtime
import pytz

class StudentLoginHistorySerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    logout_time = serializers.SerializerMethodField()

    class Meta:
        model = StudentLoginHistory
        fields = ['id', 'date', 'time', 'logout_time']

    def get_date(self, obj):
        tz = pytz.timezone("Asia/Tashkent")
        login_local = obj.login_time.astimezone(tz)
        return login_local.strftime('%d/%m/%Y')

    def get_time(self, obj):
        tz = pytz.timezone("Asia/Tashkent")
        login_local = obj.login_time.astimezone(tz)
        return login_local.strftime('%H:%M')

    def get_logout_time(self, obj):
        if obj.logout_time:
            tz = pytz.timezone("Asia/Tashkent")
            logout_local = obj.logout_time.astimezone(tz)
            return logout_local.strftime('%H:%M')
        return None