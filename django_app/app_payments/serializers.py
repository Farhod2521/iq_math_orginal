from rest_framework import serializers
from .models import UserPayment, SubscriptionPlan

class UserPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPayment
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
    price_per_month = serializers.DecimalField(  # modeldagi qiymatni ham chiqaramiz
        max_digits=10, decimal_places=2, read_only=True
    )
    sale_price = serializers.SerializerMethodField()  # chegirmali oylik narx

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id',
            'months',
            'get_months_display',
            'discount_percent',
            'price_per_month',  # modeldagi narx
            'sale_price',       # chegirmali narx (oylik)
            'is_active',
            'created_at',
            'updated_at',
        ]

    def get_sale_price(self, obj):
        """
        Chegirmali oylik narx (faqat 1 oy uchun).
        """
        # 1 oylik narx
        monthly_price = float(obj.price_per_month)
        # chegirma summasi
        discount_amount = (monthly_price * obj.discount_percent) / 100
        # chegirmali oylik narx
        return float(monthly_price - discount_amount)