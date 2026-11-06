from ckeditor.fields import RichTextField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from django_app.app_user.models import Class, Student, Subject


class LigaSeason(models.Model):
    """Raqamli mavsum: ichida haftalik testlar. Oxirgi hafta testlari tugagach avtomatik yopiladi."""
    number = models.PositiveIntegerField(unique=True, verbose_name="Mavsum raqami")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    weeks_count = models.PositiveIntegerField(default=12, verbose_name="Haftalar soni")
    prize_1_uz = models.CharField(max_length=100, default="Planshet", verbose_name="1-o'rin sovg'asi (uz)")
    prize_1_ru = models.CharField(max_length=100, default="Планшет", verbose_name="1-o'rin sovg'asi (ru)")
    prize_2_uz = models.CharField(max_length=100, default="Telefon", verbose_name="2-o'rin sovg'asi (uz)")
    prize_2_ru = models.CharField(max_length=100, default="Телефон", verbose_name="2-o'rin sovg'asi (ru)")
    prize_3_uz = models.CharField(max_length=100, default="Quloqchin", verbose_name="3-o'rin sovg'asi (uz)")
    prize_3_ru = models.CharField(max_length=100, default="Наушники", verbose_name="3-o'rin sovg'asi (ru)")
    is_published = models.BooleanField(default=False, verbose_name="E'lon qilinganmi?")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="Yopilgan vaqti")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Liga mavsumi"
        verbose_name_plural = "Liga mavsumlari"
        ordering = ['-number']

    def __str__(self):
        return f"{self.number}-mavsum"

    @property
    def is_closed(self):
        return self.closed_at is not None


class LigaTest(models.Model):
    """Haftalik test: bitta hafta, bitta sinf. Kuni, soati va ishlash vaqti shu yerda belgilanadi."""
    STATUS_DRAFT = 'draft'
    STATUS_UPCOMING = 'upcoming'
    STATUS_LIVE = 'live'
    STATUS_FINISHED = 'finished'

    season = models.ForeignKey(LigaSeason, on_delete=models.CASCADE, related_name='tests', verbose_name="Mavsum")
    grade = models.ForeignKey(Class, on_delete=models.PROTECT, related_name='liga_tests', verbose_name="Sinf")
    week_number = models.PositiveIntegerField(default=1, verbose_name="Hafta raqami")
    start_at = models.DateTimeField(verbose_name="Test boshlanish vaqti")
    end_at = models.DateTimeField(verbose_name="Testga kirish tugash vaqti")
    duration_minutes = models.PositiveIntegerField(default=60, verbose_name="Ishlash vaqti (daqiqa)")
    question_count = models.PositiveIntegerField(default=25, verbose_name="O'quvchiga tushadigan savollar soni")
    is_published = models.BooleanField(default=False, verbose_name="E'lon qilinganmi?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Liga testi"
        verbose_name_plural = "Liga testlari"
        ordering = ['start_at', 'grade_id']
        constraints = [
            models.UniqueConstraint(fields=['season', 'grade', 'week_number'], name='liga_unique_test_per_week'),
        ]

    def __str__(self):
        return f"{self.season} — {self.week_number}-hafta — {self.grade}-sinf"

    def clean(self):
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValidationError("Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak.")
        if self.start_at and self.end_at and self.duration_minutes:
            if (self.end_at - self.start_at).total_seconds() < self.duration_minutes * 60:
                raise ValidationError("Ishlash vaqti test oynasidan uzun bo'lishi mumkin emas.")

    @property
    def status(self):
        now = timezone.now()
        if not self.is_published:
            return self.STATUS_DRAFT
        if now < self.start_at:
            return self.STATUS_UPCOMING
        if now < self.end_at:
            return self.STATUS_LIVE
        return self.STATUS_FINISHED


class LigaQuestion(models.Model):
    """Testning savollar bazasi: savollar ko'p bo'lishi mumkin, o'quvchiga question_count tasi tushadi.
    Dars savollaridan alohida — darslarda ko'rinib qolmasligi uchun."""
    TYPE_CHOICE = 'choice'
    TYPE_TEXT = 'text'
    QUESTION_TYPES = [
        (TYPE_CHOICE, "Variant tanlash"),
        (TYPE_TEXT, "Matnli javob"),
    ]

    test = models.ForeignKey(LigaTest, on_delete=models.CASCADE, related_name='questions', verbose_name="Test")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='liga_questions', verbose_name="Fan")
    question_text = RichTextField(verbose_name="Savol matni")
    image = models.ImageField(upload_to="FILES/Liga", blank=True, null=True, verbose_name="Rasm")
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default=TYPE_CHOICE, verbose_name="Turi")
    correct_text_answer = models.CharField(max_length=255, blank=True, null=True, verbose_name="To'g'ri javob (matnli savol)")
    score = models.PositiveSmallIntegerField(default=1, verbose_name="Ball")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")

    class Meta:
        verbose_name = "Liga savoli"
        verbose_name_plural = "Liga savollari"
        ordering = ['order', 'id']

    def __str__(self):
        return f"{self.test} — #{self.pk}"

    def clean(self):
        if self.question_type == self.TYPE_TEXT and not self.correct_text_answer:
            raise ValidationError("Matnli savol uchun to'g'ri javob kiritilishi kerak.")
        if self.subject_id and self.test_id and self.subject.classes_id != self.test.grade_id:
            raise ValidationError("Fan test sinfiga tegishli emas.")


class LigaChoice(models.Model):
    question = models.ForeignKey(LigaQuestion, on_delete=models.CASCADE, related_name='choices')
    letter = models.CharField(max_length=1, verbose_name="Harf")  # A, B, C...
    text = RichTextField(blank=True, verbose_name="Variant matni")
    image = models.ImageField(upload_to="FILES/Liga", blank=True, null=True, verbose_name="Rasm")
    is_correct = models.BooleanField(default=False, verbose_name="To'g'ri variant")

    class Meta:
        verbose_name = "Variant"
        verbose_name_plural = "Variantlar"
        ordering = ['letter', 'id']

    def __str__(self):
        return f"{self.letter}"


class LigaParticipant(models.Model):
    """"Ligaga qatnashish" tugmasini bosgan o'quvchi. Sinf qo'shilgan paytdagi holatda saqlanadi."""
    season = models.ForeignKey(LigaSeason, on_delete=models.CASCADE, related_name='participants', verbose_name="Mavsum")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='liga_participations', verbose_name="O'quvchi")
    grade = models.ForeignKey(Class, on_delete=models.PROTECT, related_name='liga_participants', verbose_name="Sinf")
    points = models.PositiveIntegerField(default=0, verbose_name="Liga ballari")
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan vaqti")

    class Meta:
        verbose_name = "Liga ishtirokchisi"
        verbose_name_plural = "Liga ishtirokchilari"
        ordering = ['-points', 'joined_at']
        constraints = [
            models.UniqueConstraint(fields=['season', 'student'], name='liga_unique_participant'),
        ]

    def __str__(self):
        return f"{self.student} — {self.season}"


class LigaPointLog(models.Model):
    """Ball qayerdan kelgani. (participant, source, ref) yagona — bir narsa uchun ikki marta ball berilmaydi."""
    SOURCE_DAILY = 'daily'
    SOURCE_SUBJECT = 'subject'
    SOURCE_TEST = 'test'
    SOURCES = [
        (SOURCE_DAILY, "Kunlik kirish"),
        (SOURCE_SUBJECT, "Fanlarni ishlash"),
        (SOURCE_TEST, "Haftalik test"),
    ]

    participant = models.ForeignKey(LigaParticipant, on_delete=models.CASCADE, related_name='point_logs')
    source = models.CharField(max_length=10, choices=SOURCES)
    ref = models.CharField(max_length=50, verbose_name="Manba (sana, savol yoki urinish)")
    points = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Liga balli tarixi"
        verbose_name_plural = "Liga ballari tarixi"
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['participant', 'source', 'ref'], name='liga_unique_point_award'),
        ]


class LigaWinner(models.Model):
    """Mavsum yopilganda saqlanadigan g'oliblar: ballar nolga tushsa ham bu ma'lumot qoladi."""
    season = models.ForeignKey(LigaSeason, on_delete=models.CASCADE, related_name='winners', verbose_name="Mavsum")
    grade = models.ForeignKey(Class, on_delete=models.PROTECT, related_name='liga_winners', verbose_name="Sinf")
    place = models.PositiveSmallIntegerField(verbose_name="O'rin")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name='liga_wins', verbose_name="O'quvchi")
    points = models.PositiveIntegerField(default=0, verbose_name="Ballar")
    prize_uz = models.CharField(max_length=100, blank=True, verbose_name="Sovg'a (uz)")
    prize_ru = models.CharField(max_length=100, blank=True, verbose_name="Sovg'a (ru)")
    documents_checked = models.BooleanField(default=False, verbose_name="Hujjatlari tekshirilganmi?")
    is_disqualified = models.BooleanField(default=False, verbose_name="Sovg'adan mahrum qilinganmi?")
    disqualify_reason = models.CharField(max_length=255, blank=True, verbose_name="Sababi")

    class Meta:
        verbose_name = "Liga g'olibi"
        verbose_name_plural = "Liga g'oliblari"
        ordering = ['-season__number', 'grade_id', 'place']
        constraints = [
            models.UniqueConstraint(fields=['season', 'grade', 'place'], name='liga_unique_winner_place'),
        ]

    def __str__(self):
        return f"{self.season} — {self.grade}-sinf — {self.place}-o'rin"


class LigaAttempt(models.Model):
    """O'quvchining testni ishlashi. Bitta testga faqat bitta urinish."""
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_FINISHED = 'finished'
    STATUS_EXPIRED = 'expired'
    STATUSES = [
        (STATUS_IN_PROGRESS, "Ishlamoqda"),
        (STATUS_FINISHED, "Yakunlagan"),
        (STATUS_EXPIRED, "Vaqti tugagan"),
    ]

    # PROTECT: natijalari bor test tasodifan o'chirilib ketmasin
    test = models.ForeignKey(LigaTest, on_delete=models.PROTECT, related_name='attempts', verbose_name="Test")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='liga_attempts', verbose_name="O'quvchi")
    status = models.CharField(max_length=20, choices=STATUSES, default=STATUS_IN_PROGRESS, verbose_name="Holat")
    question_order = models.JSONField(default=list, verbose_name="Tushgan savollar")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Boshlagan vaqti")
    deadline_at = models.DateTimeField(verbose_name="Tugash muddati")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Yakunlagan vaqti")
    duration_seconds = models.PositiveIntegerField(null=True, blank=True, verbose_name="Ishlagan vaqti (soniya)")
    total_questions = models.PositiveIntegerField(default=0, verbose_name="Savollar soni")
    answered_count = models.PositiveIntegerField(default=0, verbose_name="Javob berilgan")
    correct_count = models.PositiveIntegerField(default=0, verbose_name="To'g'ri javoblar")
    score = models.PositiveIntegerField(default=0, verbose_name="Ball")
    max_score = models.PositiveIntegerField(default=0, verbose_name="Maksimal ball")

    class Meta:
        verbose_name = "Liga natijasi"
        verbose_name_plural = "Liga natijalari"
        ordering = ['-score', 'duration_seconds', 'finished_at']
        constraints = [
            models.UniqueConstraint(fields=['test', 'student'], name='liga_unique_attempt_per_student'),
        ]
        indexes = [
            models.Index(fields=['status', 'deadline_at'], name='liga_attempt_status_deadline'),
        ]

    def __str__(self):
        return f"{self.student} — {self.test}"

    @property
    def wrong_count(self):
        """Javob berilmagan savollar ham xato hisoblanadi."""
        return self.total_questions - self.correct_count


class LigaAnswer(models.Model):
    """Har bir javob darhol saqlanadi — sahifa yopilsa ham o'quvchi o'sha joyidan davom etadi."""
    attempt = models.ForeignKey(LigaAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(LigaQuestion, on_delete=models.PROTECT, related_name='answers')
    selected_choice = models.ForeignKey(LigaChoice, on_delete=models.PROTECT, null=True, blank=True, related_name='answers')
    text_answer = models.CharField(max_length=255, blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Liga javobi"
        verbose_name_plural = "Liga javoblari"
        constraints = [
            models.UniqueConstraint(fields=['attempt', 'question'], name='liga_unique_answer_per_question'),
        ]
