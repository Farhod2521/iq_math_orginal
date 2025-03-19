from rest_framework import serializers
from .models import Subject



class SubjectSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source="classes.name")  # Sinf nomini olish
    teachers = serializers.StringRelatedField(many=True)  # O‘qituvchi ismlarini olish

    class Meta:
        model = Subject
        fields = ["id", "name", "class_name", "teachers"]  # Kerakli maydonlar
