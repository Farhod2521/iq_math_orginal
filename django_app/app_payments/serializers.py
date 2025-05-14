from rest_framework import serializers
from .models import Payment

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