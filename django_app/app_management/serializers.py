from rest_framework import serializers
from .models import SystemSettings, FAQ, Product, Banner, ConversionRate, Category, Tag, Elon, Motivation, AndroidVersion




class AndroidVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AndroidVersion
        fields = [
            "id",
            "android_latest_version",
            "android_force_update",
            "ios_latest_version",
            "ios_force_update",
        ]

class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = '__all__'


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = '__all__'



class ProductSerializer(serializers.ModelSerializer):
    price_money = serializers.SerializerMethodField()
    price_score = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name_uz", "name_ru", "coin","count", "price_money", "price_score", "image"]

    def get_price_money(self, obj):
        rate = ConversionRate.objects.last()
        if rate:
            return obj.coin * rate.coin_to_money
        return None

    def get_price_score(self, obj):
        rate = ConversionRate.objects.last()
        if rate:
            return obj.coin * rate.coin_to_score
        return None

class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = '__all__'




class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "title"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "title"]
class ElonSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all()
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all()
    )

    class Meta:
        model = Elon
        fields = [
            "id",
            "title_uz",
            "title_ru",
            "text_uz",
            "text_ru",
            "image",
            "categories",
            "tags",
            "notification_status",
            "news_status",
            "created_at",
            "updated_at",
        ]
    def create(self, validated_data):
        categories = validated_data.pop("categories", [])
        tags = validated_data.pop("tags", [])

        elon = Elon.objects.create(**validated_data)
        elon.categories.set(categories)
        elon.tags.set(tags)

        return elon



class MotivationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Motivation
        fields = "__all__"