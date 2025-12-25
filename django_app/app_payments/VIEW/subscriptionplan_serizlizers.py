from rest_framework import serializers
from django_app.app_payments.models import SubscriptionCategory, SubscriptionBenefit

class SubscriptionCategoryReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionCategory
        fields = (
            "id",
            "title_uz",
            "title_ru",
            "slug",
            "is_active",
            "created_at",
        )

class SubscriptionCategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionCategory
        fields = (
            "title_uz",
            "title_ru",
            "slug",
            "is_active",
        )


class SubscriptionBenefitReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionBenefit
        fields = (
            "id",
            "title_uz",
            "title_ru",
            "description_uz",
            "description_ru",
            "is_active",
            "created_at",
        )

class SubscriptionBenefitCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionBenefit
        fields = (
            "title_uz",
            "title_ru",
            "description_uz",
            "description_ru",
            "is_active",
        )
