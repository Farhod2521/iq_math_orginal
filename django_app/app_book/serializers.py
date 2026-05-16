from rest_framework import serializers
from .models import Category, Tag, Book


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'name_uz', 'name_ru', 'is_active', 'created_at']
        read_only_fields = ['created_at', 'name']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'name_uz', 'name_ru', 'is_active', 'created_at']
        read_only_fields = ['created_at', 'name']


class BookReadSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = [
            'id',
            'name', 'name_uz', 'name_ru',
            'description', 'description_uz', 'description_ru',
            'category', 'tags',
            'file', 'cover_image',
            'price', 'status', 'is_offline', 'quantity', 'date',
            'for_student', 'for_teacher',
            'created_at', 'updated_at',
        ]


class BookWriteSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False
    )

    class Meta:
        model = Book
        fields = [
            'id',
            'name_uz', 'name_ru',
            'description_uz', 'description_ru',
            'category', 'tags',
            'file', 'cover_image',
            'price', 'status', 'is_offline', 'quantity', 'date',
            'for_student', 'for_teacher',
        ]
