from django.db import models
from django_app.app_user.models import Student
from django_app.app_teacher.models import Topic, Question

class  Diagnost_Student(models.Model):
    student =  models.ForeignKey(Student, on_delete=models.CASCADE)
    result   = models.JSONField()

    def __str__(self):
        return str(self.student.full_name)
    




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

    class Meta:
        unique_together = ('student_score', 'question')  
        verbose_name = "Ball olish tarixi"
        verbose_name_plural = "Ballar olish tarixi"
        ordering = ['-awarded_at']

    def __str__(self):
        return f"{self.student_score.student} - {self.question.id}"


