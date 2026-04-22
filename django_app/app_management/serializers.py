from rest_framework import serializers
from .models import SystemSettings, FAQ, Product, Banner, ConversionRate, Category, Tag, Elon, Motivation, AndroidVersion, Mathematician, DailyCoinSettings, SolutionStatus, UploadSetting




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
    about = serializers.CharField(required=False, allow_blank=True, write_only=True)
    about_uz = serializers.CharField(required=False, allow_blank=True)
    about_ru = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = SystemSettings
        fields = [
            "id",
            "logo",
            "about",
            "about_uz",
            "about_ru",
            "instagram_link",
            "telegram_link",
            "youtube_link",
            "twitter_link",
            "facebook_link",
            "linkedin_link",
            "shartnoma_uz",
            "shartnoma_ru",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def validate(self, attrs):
        if self.instance is None:
            about = attrs.get("about")
            about_uz = attrs.get("about_uz")
            about_ru = attrs.get("about_ru")

            if not any([about, about_uz, about_ru]):
                raise serializers.ValidationError(
                    {
                        "about_uz": "Kamida about_uz yoki about_ru yuborilishi kerak.",
                        "about_ru": "Kamida about_uz yoki about_ru yuborilishi kerak.",
                    }
                )

            attrs["about"] = about or about_uz or about_ru

        return attrs


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = '__all__'



class DailyCoinSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyCoinSettings
        fields = ['id', 'daily_coin_limit', 'updated_at']
        read_only_fields = ['updated_at']


class UploadSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadSetting
        fields = ['id', 'max_size_mb', 'updated_at']
        read_only_fields = ['updated_at']


class SolutionStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = SolutionStatus
        fields = ['id', 'subject_is_active', 'recommendation_is_active']


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
            "video",
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



class MathematicianListSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Mathematician
        fields = (
            "id",
            "title_uz",
            "title_ru",
            "subtitle_uz",
            "subtitle_ru",
            "life_years_uz",
            "life_years_ru",
            "image",
        )


class MathematicianDetailSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = Mathematician
        fields = (
            "id",
            "title_uz",
            "title_ru",
            "subtitle_uz",
            "subtitle_ru",
            "life_years_uz",
            "life_years_ru",
            "image",
            "description_uz",
            "description_ru",
            "created_at",
        )
