from django.db import models
from django_app.app_user.models import Student
from django_app.app_teacher.models import Topic

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