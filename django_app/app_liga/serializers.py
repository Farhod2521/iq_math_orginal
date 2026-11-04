from django.db import transaction
from rest_framework import serializers

from .models import LigaChoice, LigaQuestion, LigaSeason, LigaTest, LigaWinner


# ---------- O'quvchi: to'g'ri javob hech qachon yuborilmaydi ----------

class StudentChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LigaChoice
        fields = ('id', 'letter', 'text_uz', 'text_ru')


class StudentQuestionSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    choices = StudentChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = LigaQuestion
        fields = (
            'id', 'subject', 'subject_name', 'question_type',
            'question_text_uz', 'question_text_ru', 'image', 'score', 'choices',
        )


class PublicSeasonSerializer(serializers.ModelSerializer):
    is_closed = serializers.BooleanField(read_only=True)

    class Meta:
        model = LigaSeason
        fields = (
            'id', 'number', 'description_uz', 'description_ru', 'weeks_count', 'is_closed', 'closed_at',
            'prize_1_uz', 'prize_1_ru', 'prize_2_uz', 'prize_2_ru', 'prize_3_uz', 'prize_3_ru',
        )


class AnswerInputSerializer(serializers.Serializer):
    question = serializers.IntegerField()
    choice = serializers.IntegerField(required=False, allow_null=True)
    text_answer = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)


# ---------- Mentor / admin ----------

class AdminSeasonSerializer(serializers.ModelSerializer):
    is_closed = serializers.BooleanField(read_only=True)
    tests_count = serializers.IntegerField(source='tests.count', read_only=True)
    participants_count = serializers.IntegerField(source='participants.count', read_only=True)

    class Meta:
        model = LigaSeason
        fields = (
            'id', 'number', 'description_uz', 'description_ru', 'weeks_count',
            'prize_1_uz', 'prize_1_ru', 'prize_2_uz', 'prize_2_ru', 'prize_3_uz', 'prize_3_ru',
            'is_published', 'is_closed', 'closed_at', 'tests_count', 'participants_count', 'created_at',
        )
        read_only_fields = ('closed_at', 'created_at')


def validate_test_window(start, end, duration):
    if end <= start:
        raise serializers.ValidationError("Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak.")
    if (end - start).total_seconds() < duration * 60:
        raise serializers.ValidationError("Ishlash vaqti test oynasidan uzun bo'lishi mumkin emas.")


class AdminTestSerializer(serializers.ModelSerializer):
    grade_name = serializers.CharField(source='grade.name', read_only=True)
    status = serializers.CharField(read_only=True)
    questions_total = serializers.IntegerField(source='questions.count', read_only=True)
    attempts_count = serializers.IntegerField(source='attempts.count', read_only=True)

    class Meta:
        model = LigaTest
        fields = (
            'id', 'season', 'grade', 'grade_name', 'week_number', 'start_at', 'end_at', 'duration_minutes',
            'question_count', 'is_published', 'status', 'questions_total', 'attempts_count', 'created_at',
        )
        read_only_fields = ('created_at',)

    def validate(self, attrs):
        def value(name, default=None):
            return attrs.get(name, getattr(self.instance, name, default))

        validate_test_window(value('start_at'), value('end_at'), value('duration_minutes', 60))
        if value('is_published') and not (self.instance and self.instance.questions.exists()):
            raise serializers.ValidationError("Savollarsiz testni e'lon qilib bo'lmaydi.")

        if self.instance and self.instance.attempts.exists():
            for name in ('season', 'grade', 'week_number', 'start_at', 'duration_minutes', 'question_count'):
                if name in attrs and attrs[name] != getattr(self.instance, name):
                    raise serializers.ValidationError("Test boshlangan: faqat tugash vaqtini o'zgartirish mumkin.")
        return attrs


class BulkTestSerializer(serializers.Serializer):
    """Bitta hafta testini bir nechta sinf uchun birdan yaratish."""
    season = serializers.PrimaryKeyRelatedField(queryset=LigaSeason.objects.all())
    grades = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    week_number = serializers.IntegerField(min_value=1)
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(min_value=1)
    question_count = serializers.IntegerField(min_value=1, default=25)

    def validate(self, attrs):
        validate_test_window(attrs['start_at'], attrs['end_at'], attrs['duration_minutes'])
        return attrs


class AdminChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LigaChoice
        fields = ('id', 'letter', 'text_uz', 'text_ru', 'is_correct')


class AdminQuestionSerializer(serializers.ModelSerializer):
    choices = AdminChoiceSerializer(many=True, required=False)
    subject_name = serializers.CharField(source='subject.name', read_only=True)

    class Meta:
        model = LigaQuestion
        fields = (
            'id', 'test', 'subject', 'subject_name', 'question_text_uz', 'question_text_ru', 'image',
            'question_type', 'correct_text_answer', 'score', 'order', 'choices',
        )
        extra_kwargs = {'question_text_uz': {'required': True}}

    def validate(self, attrs):
        def value(name):
            return attrs.get(name, getattr(self.instance, name, None))

        test, subject = value('test'), value('subject')
        if subject.classes_id != test.grade_id:
            raise serializers.ValidationError("Fan test sinfiga tegishli emas.")

        if value('question_type') == LigaQuestion.TYPE_TEXT:
            if not value('correct_text_answer'):
                raise serializers.ValidationError("Matnli savol uchun to'g'ri javob kiritilishi kerak.")
        elif 'choices' in attrs or not self.instance:
            choices = attrs.get('choices') or []
            if len(choices) < 2:
                raise serializers.ValidationError("Kamida 2 ta variant kerak.")
            if sum(1 for choice in choices if choice.get('is_correct')) != 1:
                raise serializers.ValidationError("Aynan bitta to'g'ri variant bo'lishi kerak.")
        return attrs

    def _save_choices(self, question, choices):
        question.choices.all().delete()
        LigaChoice.objects.bulk_create([LigaChoice(question=question, **choice) for choice in choices])

    @transaction.atomic
    def create(self, validated_data):
        choices = validated_data.pop('choices', [])
        question = super().create(validated_data)
        self._save_choices(question, choices)
        return question

    @transaction.atomic
    def update(self, instance, validated_data):
        choices = validated_data.pop('choices', None)
        question = super().update(instance, validated_data)
        if choices is not None:
            self._save_choices(question, choices)
        return question


class AdminWinnerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='student.full_name', read_only=True)
    phone = serializers.CharField(source='student.user.phone', read_only=True)
    grade_name = serializers.CharField(source='grade.name', read_only=True)
    season_number = serializers.IntegerField(source='season.number', read_only=True)

    class Meta:
        model = LigaWinner
        fields = (
            'id', 'season', 'season_number', 'grade', 'grade_name', 'place', 'student', 'full_name', 'phone',
            'points', 'prize_uz', 'prize_ru', 'documents_checked', 'is_disqualified', 'disqualify_reason',
        )
        read_only_fields = (
            'season', 'grade', 'place', 'student', 'points', 'prize_uz', 'prize_ru',
        )
