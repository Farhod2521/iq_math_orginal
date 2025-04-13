from django.db import models
from django_app.app_user.models import Student


class  Diagnost_Student(models.Model):
    student =  models.ForeignKey(Student, on_delete=models.CASCADE)
    result   = models.JSONField()

    def __str__(self):
        return str(self.student.full_name)