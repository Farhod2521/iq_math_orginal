from rest_framework import serializers
from .models import Payment, SubscriptionPlan, SubscriptionBenefit

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id',
            'store_id',             # Multicard ID raqami
            'student',              # Talaba
            'invoice_uuid',         # Invoys ID raqami
            'uuid',                 # To‘lov tranzaksiyasining ID raqami
            'billing_id',           # Hamkor billing tizimidagi tranzaksiya ID
            'sign',                 # MD5 HASH
            'amount',               # To‘lov summasi
            'payment_date',         # To‘lov sanasi
            'transaction_id',       # Tranzaksiya ID
            'status',               # Holat
            'payment_gateway',      # To‘lov tizimi
            'receipt_url'           # Chek havolasi
        ]
class SubscriptionBenefitStatusSerializer(serializers.ModelSerializer):
    is_selected = serializers.BooleanField()

    class Meta:
        model = SubscriptionBenefit
        fields = (
            "id",
            "title",
            "description",
            "is_selected",
        )

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    price_per_month = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    sale_price = serializers.SerializerMethodField()
    benefits = serializers.SerializerMethodField()
    months_display = serializers.CharField(
        source="get_months_display",
        read_only=True
    )

    category = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",          # ✅ plan nomi
            "category",      # ✅ category title
            "months",
            "months_display",
            "discount_percent",
            "price_per_month",
            "sale_price",
            "benefits",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_category(self, obj):
        if obj.category:
            return {
                "id": obj.category.id,
                "title": obj.category.title
            }
        return None

    def get_sale_price(self, obj):
        monthly_price = float(obj.price_per_month)
        discount_amount = (monthly_price * obj.discount_percent) / 100
        return monthly_price - discount_amount

    def get_benefits(self, obj):
        all_benefits = SubscriptionBenefit.objects.filter(is_active=True)
        plan_benefit_ids = obj.benefits.values_list("id", flat=True)

        return [
            {
                "id": benefit.id,
                "title": benefit.title,
                "description": benefit.description,
                "is_selected": benefit.id in plan_benefit_ids
            }
            for benefit in all_benefits
        ]

    

class PaymentTeacherSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    coupon_code = serializers.CharField(source="coupon.code", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "student_name",
            "amount",
            "original_amount",
            "discount_percent",
            "coupon_code",
            "coupon_type",
            "status",
            "payment_gateway",
            "student_cashback_amount",
            "teacher_cashback_amount",
            "payment_date",
            "created_at",
        ]


class SubscriptionPlanCREATESerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "category",        # category_id keladi
            "months",
            "benefits",        # benefit_id lar list
            "discount_percent",
            "price_per_month",
            "is_active",
        ]


class SubscriptionREADPlanSerializer(serializers.ModelSerializer):
    months_display = serializers.CharField(
        source="get_months_display",
        read_only=True
    )
    sale_price = serializers.SerializerMethodField()
    benefits = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "name",
            "category",
            "months",
            "months_display",
            "discount_percent",
            "price_per_month",
            "sale_price",
            "benefits",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_category(self, obj):
        if obj.category:
            return {
                "id": obj.category.id,
                "title": obj.category.title
            }
        return None

    def get_sale_price(self, obj):
        monthly_price = float(obj.price_per_month)
        discount_amount = (monthly_price * obj.discount_percent) / 100
        return monthly_price - discount_amount

    def get_benefits(self, obj):
        all_benefits = SubscriptionBenefit.objects.filter(is_active=True)
        plan_benefit_ids = obj.benefits.values_list("id", flat=True)

        return [
            {
                "id": b.id,
                "title": b.title,
                "description": b.description,
                "is_selected": b.id in plan_benefit_ids
            }
            for b in all_benefits
        ]
