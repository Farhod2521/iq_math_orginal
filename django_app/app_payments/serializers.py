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
    price_total = serializers.SerializerMethodField()  # jami narx (chegirmasiz)
    total_price = serializers.SerializerMethodField()  # chegirma bilan

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id',
            'months',
            'get_months_display',
            'discount_percent',
            'price_total',    # yangi – jami narx
            'total_price',    # chegirmali narx
            'is_active',
            'created_at',
            'updated_at',
        ]

    def get_price_total(self, obj):
        """Chegirmasiz jami narx"""
        return float(obj.months * obj.price_per_month)

    def get_total_price(self, obj):
        """Chegirmali jami narx"""
        full_price = obj.months * obj.price_per_month
        discount_amount = (full_price * obj.discount_percent) / 100
        return float(full_price - discount_amount)