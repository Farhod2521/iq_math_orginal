from django.db import models
from django_app.app_user.models import  Subject
from ckeditor.fields import RichTextField
from django_app.app_management.models import Product
from django_app.app_user.models import Teacher, Student

from ckeditor.fields import RichTextField
class Chapter(models.Model):
    name = models.CharField(max_length=500, verbose_name="Bob nomi")
    subject = models.ForeignKey(
        Subject, on_delete=models.SET_NULL,
        related_name="chapters", verbose_name="Tegishli fan",
        null=True
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")  # ✅ Qo‘shildi

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Fan Bobi"
        verbose_name_plural = "Fan Boblari"
        ordering = ['order']  # ✅ Tartiblash

class Topic(models.Model):
    name = models.CharField(max_length=200, verbose_name="Mavzu nomi")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="topics", verbose_name="Tegishli bob")
    video_url_uz = models.URLField(blank=True, null=True, verbose_name="Mavzu videosi")
    video_url_ru = models.URLField(blank=True, null=True, verbose_name="Mavzu videosi")
    content = RichTextField(verbose_name="Mavzu matni", blank=True, null=True)
    is_locked = models.BooleanField(default=True, verbose_name="Qulflangan")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Mavzu"
        verbose_name_plural = "Mavzular"
        ordering = ['order'] 




from django.core.exceptions import ValidationError
class Question(models.Model):
    QUESTION_TYPES = [
        ('text', "Matnli javob"),
        ('choice', "Variant tanlash"),
        ('image_choice', "Rasmli variant"),
        ('composite', "Bir nechta inputli savol"),
    ]

    topic = models.ForeignKey("Topic", on_delete=models.CASCADE, related_name="questions")
    question_text = RichTextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    level = models.PositiveIntegerField()
    
    # Faqat text turi uchun
    correct_text_answer = RichTextField(blank=True, null=True)
    video_file_uz = models.FileField(upload_to="Video_darsliklar/", null=True, blank=True)
    video_file_ru = models.FileField(upload_to="Video_darsliklar/", null=True, blank=True)
    video_url_uz  = models.URLField(null=True, blank=True)
    video_url_ru  = models.URLField(null=True, blank=True)

    def __str__(self):
        return f"{self.question_text[:30]}..."
    def clean(self):
        if self.question_type == 'text' and not self.correct_text_answer:
            raise ValidationError("Matnli savollar uchun to‘g‘ri javob kiritilishi kerak.")
        if self.question_type in ['choice', 'image_choice'] and not self.pk:
            # Can't validate related objects until instance is saved
            return
        if self.question_type in ['choice', 'image_choice'] and not self.choices.exists():
            raise ValidationError("Variantli savollar uchun hech bo‘lmasa bitta variant bo‘lishi kerak.")
        if self.question_type == 'composite' and not self.sub_questions.exists():
            raise ValidationError("Bir nechta inputli savollar uchun kamida bitta kichik savol bo‘lishi kerak.")
    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
class CompositeSubQuestion(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='sub_questions')
    text1 = models.TextField(blank=True, null=True)  
    correct_answer = models.CharField(max_length=255)
    text2 =  models.TextField(blank=True, null=True)

    def __str__(self):
        return self.text1
    class Meta:
        verbose_name = "Kichik savol"
        verbose_name_plural = "Kichik savollar"
    
class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    letter = models.CharField(max_length=1)  # A, B, C...
    text = RichTextField(blank=True, null=True)
    image = models.ImageField(upload_to='choices/images/', blank=True, null=True)
    is_correct = models.BooleanField(default=False)  # To‘g‘ri variant

    def __str__(self):
        return f"{self.letter} - {self.text or self.image.url}"
    class Meta:
        verbose_name = "Variant"
        verbose_name_plural = "Variantlar"





class UnsolvedQuestionReport(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ko‘rib chiqilmoqda'),
        ('answered', 'Javob yozildi'),
    ]

    question = models.ForeignKey("Question", on_delete=models.CASCADE, related_name="unsolved_reports")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="unsolved_reports")
    teachers = models.ManyToManyField(Teacher, related_name="unsolved_reports")  # Subject teacherlari
    message = models.TextField(verbose_name="Izoh", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    answered_by = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name="answered_reports")
    answer = RichTextField(verbose_name="O‘qituvchi javobi", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.full_name} - {self.question}"

    class Meta:
        verbose_name = "Ishlanmagan savol"
        verbose_name_plural = "Ishlanmagan savollar"


class Group(models.Model):
    name = models.CharField(max_length=200, verbose_name="Guruh nomi")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="groups", verbose_name="O'qituvchi")
    students = models.ManyToManyField(Student, related_name="groups", blank=True, verbose_name="O'quvchilar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"



class TeacherScore(models.Model):
    teacher = models.OneToOneField(Teacher, on_delete=models.CASCADE)
    score = models.PositiveIntegerField(default=0)
    coin = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "O‘qituvchi bali"
        verbose_name_plural = "O‘qituvchilar ballari"
        ordering = ['-score']

    def __str__(self):
        return f"{self.teacher.full_name} - {self.score} ball"
    

class TeacherProductExchange(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('approved', 'Tasdiqlangan'),
        ('rejected', 'Rad etilgan'),
    )

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='product_exchanges')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    used_coin = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "O‘qituvchining mahsulot almashtiruvi"
        verbose_name_plural = "O‘qituvchilarning mahsulot almashtiruvi"

    def __str__(self):
        return f"{self.teacher.full_name} → {self.product.name} ({self.used_coin} tanga)"



class TeacherRewardLog(models.Model):
    REWARD_TYPES = [
        ('score', 'Ball qo‘shildi'),
        ('coin', 'Tanga qo‘shildi'),
        ('subscription_day', 'Obuna kuni qo‘shildi'),
    ]

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='given_rewards', verbose_name="O‘qituvchi")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='received_rewards', verbose_name="O‘quvchi")
    
    reward_type = models.CharField(max_length=20, choices=REWARD_TYPES, verbose_name="Rag‘bat turi")
    amount = models.PositiveIntegerField(verbose_name="Qiymati (ball, tanga yoki kun)")
    reason = models.TextField(blank=True, null=True, verbose_name="Sababi (ixtiyoriy)")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Berilgan vaqti")

    def __str__(self):
        return f"{self.teacher.full_name} → {self.student.full_name} ({self.get_reward_type_display()} - {self.amount})"

    class Meta:
        verbose_name = "Rag‘bat yozuvi"
        verbose_name_plural = "Rag‘bat yozuvlari"
        ordering = ['-created_at']








class GeneratedQuestionOpenAi(models.Model):
    base_question = models.ForeignKey(
        Question, on_delete=models.CASCADE,
        related_name='generated_versions', verbose_name="Asosiy savol"
    )
    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE,
        related_name='generated_questions', verbose_name="Tegishli mavzu"
    )
    generated_text = RichTextField(verbose_name="AI generatsiya qilgan savol")
    correct_answer = models.CharField(max_length=255, blank=True, null=True)
    data_seed = models.JSONField(blank=True, null=True, verbose_name="Raqamli parametrlar (AI tomonidan)")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by_ai = models.BooleanField(default=True)

    def __str__(self):
        return f"AI-{self.base_question.id}: {self.generated_text[:40]}"

    class Meta:
        verbose_name = "Generatsiya qilingan savol"
        verbose_name_plural = "Generatsiya qilingan savollar"
        ordering = ['-created_at']


class GeneratedChoiceOpenAi(models.Model):
    generated_question = models.ForeignKey(
        'GeneratedQuestionOpenAi',
        on_delete=models.CASCADE,
        related_name='generated_choices'
    )
    letter = models.CharField(max_length=1)
    text = RichTextField(blank=True, null=True)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.letter}. {self.text[:50]}"

    class Meta:
        verbose_name = "AI variant"
        verbose_name_plural = "AI variantlar"


class GeneratedSubQuestionOpenAi(models.Model):
    generated_question = models.ForeignKey(
        'GeneratedQuestionOpenAi',
        on_delete=models.CASCADE,
        related_name='generated_sub_questions'
    )
    text1 = models.TextField(blank=True, null=True)
    correct_answer = models.CharField(max_length=255)
    text2 = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.text1} ..."

    class Meta:
        verbose_name = "AI kichik savol"
        verbose_name_plural = "AI kichik savollar"