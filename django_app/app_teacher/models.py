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

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Mavzu"
        verbose_name_plural = "Mavzular"


class Question(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="questions", verbose_name="Tegishli mavzu")
    question_text = RichTextField(verbose_name="Savol matni")
    correct_answer = RichTextField(verbose_name="To‘g‘ri javob")
    level = models.PositiveIntegerField(verbose_name="Savol darajasi")


    def __str__(self):
        return self.question_text

    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"