from rest_framework import serializers
from .models import Payment, SubscriptionPlan

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

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id',
            'months',
            'get_months_display',  # foydalanuvchiga ko'rinadigan nom
            'discount_percent',
            'price_per_month',
            'total_price',
            'is_active',
            'created_at',
            'updated_at',
        ]

    def get_total_price(self, obj):
        return obj.total_price()