from rest_framework import serializers
from .models import Category, Tag, Book


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class BookReadSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = [
            'id', 'name', 'description', 'category', 'tags',
            'price', 'status', 'date', 'created_at', 'updated_at'
        ]


class BookWriteSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False
    )

    class Meta:
        model = Book
        fields = [
            'id', 'name', 'description', 'category', 'tags',
            'price', 'status', 'date'
        ]
