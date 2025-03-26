from django.db import models
from django_app.app_user.models import Class, Teacher
from ckeditor.fields import RichTextField


class Subject_Category(models.Model):
    name  = models.CharField(max_length=200, verbose_name="Fan bo'limi")

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "Fan Bo'limi"
        verbose_name_plural = "Fan Bo'limi"

class Subject(models.Model):
    name = models.CharField(max_length=200, verbose_name="Fan nomi")
    image = models.ImageField(upload_to="FILES/Subject", blank=True, null=True)
    teachers = models.ManyToManyField(Teacher, related_name="subjects", verbose_name="O‘qituvchilar")
    classes = models.ForeignKey(Class, on_delete=models.SET_NULL, related_name="subjects", verbose_name="Sinf", null=True)
    category = models.ForeignKey(Subject_Category, on_delete=models.SET_NULL, related_name="subjects", verbose_name="Fan bo'limi", null=True)

    def __str__(self):
        return f"{self.name} - {self.classes.name}"

    class Meta:
        verbose_name = "Fan"
        verbose_name_plural = "Fanlar"

class Chapter(models.Model):
    name = models.CharField(max_length=500, verbose_name="Bob nomi")
    subject = models.ForeignKey(Subject,on_delete=models.SET_NULL,related_name="chapters",verbose_name="Tegishli fan", null=True )

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "Fan Bobi"
        verbose_name_plural = "Fan Bobi"

class Topic(models.Model):
    name = models.CharField(max_length=200, verbose_name="Mavzu nomi")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="topics", verbose_name="Tegishli bob")
    video_url = models.URLField(blank=True, null=True, verbose_name="Mavzu videosi")
    content = RichTextField(verbose_name="Mavzu matni", blank=True, null=True)
    is_locked = models.BooleanField(default=True, verbose_name="Qulflangan")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Mavzu"
        verbose_name_plural = "Mavzular"


class Question(models.Model):
    QUESTION_TYPES = (
        ('text', "Matnli javob"),
        ('choice', "Variant tanlash"),
        ('image_choice', "Rasmli variant"),
    )
    
    topic = models.ForeignKey("Topic", on_delete=models.CASCADE, related_name="questions", verbose_name="Tegishli mavzu")
    question_text = RichTextField(verbose_name="Savol matni")
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, verbose_name="Savol turi")
    correct_answer = RichTextField(verbose_name="To‘g‘ri javob", blank=True, null=True)
    level = models.PositiveIntegerField(verbose_name="Savol darajasi")
    choices = models.JSONField(blank=True, null=True, verbose_name="Variantlar")

    def __str__(self):
        return self.question_text

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"

class QuestionImage(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="images", verbose_name="Savol")
    image = models.ImageField(upload_to="questions/images/", verbose_name="Rasm")
    choice_letter = models.CharField(max_length=1, verbose_name="Variant harfi")  # Masalan: A, B, C

    def __str__(self):
        return f"{self.choice_letter} - {self.image.url}"

    class Meta:
        verbose_name = "Savol Rasmi"
        verbose_name_plural = "Savol Rasmlari"