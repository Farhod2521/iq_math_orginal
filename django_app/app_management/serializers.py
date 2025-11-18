from rest_framework import serializers
from .models import SystemSettings, FAQ, Product, Banner, ConversionRate, Category, Tag, Elon





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
    categories = CategorySerializer(many=True)
    tags = TagSerializer(many=True)

    class Meta:
        model = Elon
        fields = [
            "id",
            "title",
            "text",
            "image",
            "categories",
            "tags",
            "created_at",
            "updated_at",
        ]