from rest_framework import serializers
from django_app.app_teacher.models import Chapter, Choice, CompositeSubQuestion, Question, Topic
from modeltranslation.utils import get_translation_fields

from django_app.app_user.models import  Subject, Student, StudentLoginHistory
from .models import TopicProgress, ChapterProgress, TopicHelpRequestIndependent, StudentReferral
from django.db.models import Sum, Count, Max
from django_app.app_user.models import Subject_Category
class SubjectStatsMobileAppSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="classes.name")
    chapters_count = serializers.IntegerField()
    topics_count = serializers.IntegerField()
    questions_count = serializers.IntegerField()

    class Meta:
        model = Subject
        fields = [
            "id",
            "name_uz",
            "name_ru",
            "class_name",
            "chapters_count",
            "topics_count",
            "questions_count"
        ]

class SubjectCategoryDetailSerializer(serializers.ModelSerializer):
    subjects = serializers.SerializerMethodField()
    subjects_count = serializers.IntegerField()

    class Meta:
        model = Subject_Category
        fields = [
            "id",
            "name_uz",
            "name_ru",
            "subjects_count",
            "subjects"
        ]

    def get_subjects(self, obj):
        subjects = (
            Subject.objects.filter(category=obj)
            .annotate(
                chapters_count=Count("chapters", distinct=True),
                topics_count=Count("chapters__topics", distinct=True),
                questions_count=Count("chapters__topics__questions", distinct=True),
            )
            .order_by("order")
        )
        return SubjectStatsMobileAppSerializer(subjects, many=True).data


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
        class_name = obj.classes.name if obj.classes else ""
        if class_name.isdigit():
            return f"{class_name}-sinf {obj.name_uz}"
        return obj.name_uz

    def get_class_ru(self, obj):
        class_name = obj.classes.name if obj.classes else ""
        if class_name.isdigit():
            return f"{class_name}-класс {obj.name_ru}"
        return obj.name_ru

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

        # 👨‍🏫 Agar foydalanuvchi o'qituvchi yoki admin bo'lsa, progress 100%
        if user.role in ['teacher', 'admin']:
            return 100.0

        try:
            student = Student.objects.get(user=user)
        except Student.DoesNotExist:
            return 0.0

        # 🔹 Shu bobga tegishli barcha topiclar
        topics = Topic.objects.filter(chapter=chapter)
        total_topics = topics.count()

        if total_topics == 0:
            return 0.0

        # 🔹 Shu bobdagi barcha mavzularda studentning progresslarini olamiz
        progresses = TopicProgress.objects.filter(user=student, topic__in=topics)

        if not progresses.exists():
            return 0.0

        # 🔹 O'rtacha score hisoblanadi
        total_score = sum(p.score for p in progresses)
        avg_score = total_score / total_topics

        # 100 dan oshib ketmasligi uchun
        return round(min(avg_score, 100), 2)


class Chapter_STUDENT_ID_Serializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ['id', 'name_uz', 'name_ru', 'subject', 'progress']

    def get_progress(self, chapter):
        student = self.context.get("student")

        # 👨‍🏫 Agar teacher/admin bo'lsa progress 100%
        if student.user.role in ['teacher', 'admin']:
            return 100.0

        topics = Topic.objects.filter(chapter=chapter)
        total_topics = topics.count()

        if total_topics == 0:
            return 0.0

        progresses = TopicProgress.objects.filter(
            user=student, topic__in=topics
        )

        if not progresses.exists():
            return 0.0

        total_score = sum(p.score for p in progresses)
        avg_score = total_score / total_topics

        return round(min(avg_score, 100), 2)


class TopicSerializer1(serializers.ModelSerializer):
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = ['id', 'name_uz', 'name_ru', 'chapter', "video_url_uz", "video_url_ru","content_uz", "content_ru", "is_locked"]

    def get_is_locked(self, obj):
        # Barcha mavzular ochiq — oldingi mavzudan 80% talab qilinmaydi
        return False

class Topic_STUDENT_ID_Serializer(serializers.ModelSerializer):
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

    # ================================
    # SCORE
    # ================================
    def get_score(self, obj):
        if self.context.get("is_staff"):
            return None  # Admin/Teacher -> score ko'rsatilmaydi

        student = self.context.get("student")

        progress = TopicProgress.objects.filter(
            user=student, topic=obj
        ).first()

        return round(progress.score, 1) if progress else 0.0

    # ================================
    # LOCKED
    # ================================
    def get_is_locked(self, obj):
        # Barcha mavzular ochiq — oldingi mavzudan 80% talab qilinmaydi
        return False

    # ================================
    # OPEN
    # ================================
    def get_is_open(self, obj):
        # Barcha mavzular ochiq — oldingi mavzudan 80% talab qilinmaydi
        return True

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
            return None  # 👨‍🏫 Admin va teacher uchun score ko'rsatilmaydi

        try:
            student = Student.objects.get(user=user)
            progress = TopicProgress.objects.get(user=student, topic=obj)
            return round(progress.score, 1)
        except (Student.DoesNotExist, TopicProgress.DoesNotExist):
            return 0.0

    def get_is_locked(self, obj):
        # Barcha mavzular ochiq — oldingi mavzudan 80% talab qilinmaydi
        return False

    def get_is_open(self, obj):
        # Barcha mavzular ochiq — oldingi mavzudan 80% talab qilinmaydi
        return True


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'letter', 'image_url'] + get_translation_fields('text')


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
                    if sub_question.get("text1_uz") in [None, "undefined"]:
                        sub_question["text2_uz"] = ""
                    if sub_question.get("text1_ru") in [None, "undefined"]:
                        sub_question["text1_ru"] = ""

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

        # 🧠 SYSTEM JAVOBLARNI QO'SHISH + SAVOL TURINI QO'SHISH
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

class MyTopicHelpRequestIndependentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicHelpRequestIndependent
        fields = '__all__'

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
    

class TopicHelpRequestIndependentDetailSerializer(serializers.ModelSerializer):
    subject_name_uz = serializers.SerializerMethodField()
    chapter_name_uz = serializers.SerializerMethodField()
    topic_name_uz = serializers.SerializerMethodField()
    result = serializers.JSONField(source='result_json', read_only=True)
    url = serializers.SerializerMethodField()  # 🔹 qo'shildi

    class Meta:
        model = TopicHelpRequestIndependent
        fields = [
            'subject_name_uz',
            'chapter_name_uz',
            'topic_name_uz',
            'result',
            'status',
            'url',
        ]

    def get_subject_name_uz(self, obj):
        subject = obj.subject
        if subject and getattr(subject, 'classes', None):  
            return f"{subject.classes.name}-sinf {subject.name}"
        elif subject:
            return subject.name
        return None

    def get_chapter_name_uz(self, obj):
        return [ch.name_uz for ch in obj.chapters.all()]

    def get_topic_name_uz(self, obj):
        return [tp.name_uz for tp in obj.topics.all()]

    def get_url(self, obj):
        # 🔹 model id + student id
        model_id = obj.id
        student_id = obj.student.id if obj.student else ''
        return f"https://t.me/iq_mathbot?start={model_id}_{student_id}"
    


class DiagnostSubjectSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name_uz = serializers.CharField()
    name_ru = serializers.CharField()
    class_name = serializers.CharField()
    class_uz = serializers.CharField()
    class_ru = serializers.CharField()
    image_uz = serializers.CharField(allow_null=True)
    image_ru = serializers.CharField(allow_null=True)
    mastery_percent = serializers.FloatField()

from django_app.app_management.models  import   Coupon_Tutor_Student

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon_Tutor_Student
        fields = ['id', 'code', 'discount_percent', 'valid_from', 'valid_until', 'is_active']
class StudentCouponCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon_Tutor_Student
        # 'code' foydalanuvchi tomonidan yuborilmaydi — viewsetda avtomatik yaratiladi
        fields = ['id']

    def validate(self, attrs):
        request = self.context.get('request')

        if not request or not hasattr(request, 'user') or request.user.is_anonymous:
            raise serializers.ValidationError({"error": "Foydalanuvchi aniqlanmadi"})

        student = getattr(request.user, 'student_profile', None)
        if student is None:
            raise serializers.ValidationError({"error": "Foydalanuvchi o'quvchi emas"})

        # Har bir o'quvchiga faqat bitta kupon
        if Coupon_Tutor_Student.objects.filter(created_by_student=student).exists():
            raise serializers.ValidationError({"error": "Siz allaqachon kupon yaratgansiz"})

        attrs['created_by_student'] = student
        return attrs

    def create(self, validated_data):
        # Kupon kodi viewset ichida generate qilinadi
        return Coupon_Tutor_Student.objects.create(**validated_data)