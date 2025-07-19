from django.db import models
from django_app.app_user.models import Student, Teacher
from django_app.app_teacher.models import Topic, Question, Chapter
from django_app.app_management.models import Product
from django_app.app_user.models import Subject

class Diagnost_Student(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True)  
    chapters = models.ManyToManyField(Chapter, blank=True)  
    topic = models.ManyToManyField(Topic, blank=True)       
    level = models.PositiveIntegerField()
    result = models.JSONField()

    def __str__(self):
        return f"{self.student.full_name} - {self.subject}"



class ChapterProgress(models.Model):
    user = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='chapter_progress')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='progress')
    progress_percentage = models.FloatField(default=0.0)  # 0 - 100

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'chapter')
        verbose_name = "Bob bo‘yicha yutuq"
        verbose_name_plural = "Boblar bo‘yicha yutuqlar"

    def __str__(self):
        return f"{self.user} - {self.chapter.name} - {self.progress_percentage}%"

class TopicProgress(models.Model):
    user = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='topic_progress')
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='progress')
    score = models.FloatField(default=0.0)  # Testdagi ball (0 - 100)
    is_unlocked = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.topic.name} - {self.score}%"

    class Meta:
        verbose_name = "Mavzu bo‘yicha yutuq"
        verbose_name_plural = "Mavzular bo‘yicha yutuqlar"
        ordering = ['-completed_at']




class StudentScore(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    score = models.PositiveIntegerField(default=0)
    coin = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        unique_together = ('student',)
        verbose_name = "Talaba bali"
        verbose_name_plural = "Talabalar ballari"
        ordering = ['-score']

    def __str__(self):
        return f"{self.student.user.username} - {self.score} ball"


class StudentScoreLog(models.Model):
    student_score = models.ForeignKey(StudentScore, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)
    awarded_coin = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student_score', 'question')  
        verbose_name = "Ball olish tarixi"
        verbose_name_plural = "Ballar olish tarixi"
        ordering = ['-awarded_at']

    def __str__(self):
        return f"{self.student_score.student} - {self.question.id}"


class ProductExchange(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('approved', 'Tasdiqlangan'),
        ('rejected', 'Rad etilgan'),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='product_exchanges')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    used_coin  = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mahsulotga almashtirish"
        verbose_name_plural = "Mahsulotga almashtirishlar"

    def __str__(self):
        return f"{self.student.full_name} → {self.product.name} ({self.used_coin} ball)"
    

class TopicHelpRequestIndependent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='student_results')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    chapters = models.ManyToManyField(Chapter)
    topics = models.ManyToManyField(Topic)
    level = models.PositiveSmallIntegerField(default=1)
    question_json = models.JSONField()
    result_json = models.JSONField()    

    # ✅ Bu yerda null va blank qilish kerak
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        verbose_name="Tekshiruvchi o‘qituvchi",
        null=True,
        blank=True
    )

    commit = models.TextField(null=True, blank=True, verbose_name="O‘qituvchi izohi")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Tekshirilgan vaqt")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} - {self.subject}"



class StudentReferral(models.Model):
    referrer = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='referred_students')  # Taklif qilgan
    referred = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='referred_by')     # Yangi ro'yxatdan o'tgan
    referred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Student referali"
        verbose_name_plural = "Student referallari"

    def __str__(self):
        return f"{self.referred.full_name} ← {self.referrer.full_name}"