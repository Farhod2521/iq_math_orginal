from rest_framework import serializers
from django_app.app_teacher.models import Subject

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name', 'teachers']
