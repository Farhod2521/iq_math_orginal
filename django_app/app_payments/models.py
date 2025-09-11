from django.db import models
from django_app.app_user.models import Student

class SubscriptionSetting(models.Model):
    free_trial_days = models.PositiveIntegerField(default=7, verbose_name="Tekin muddat (kun)")

    def __str__(self):
        return f"Tekin muddat: {self.free_trial_days} kun"
    
    class Meta:
        verbose_name = "Obuna sozlamasi"
        verbose_name_plural = "Obuna sozlamalari"



class Subscription(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='subscription')
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    next_payment_date = models.DateTimeField(null=True, blank=True, verbose_name="Keyingi to‘lov muddati")

    is_paid = models.BooleanField(default=False, verbose_name="To‘langanmi")

    def __str__(self):
        return f"{self.student.full_name} - {'To‘langan' if self.is_paid else 'Tekin'}"

    class Meta:
        verbose_name = "Obuna"
        verbose_name_plural = "Obunalar"



class Payment(models.Model):
    store_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="Multicard ID raqami")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="payments")
    invoice_uuid = models.CharField(max_length=100, null=True, blank=True, verbose_name="Invoys ID raqami")
    uuid = models.CharField(max_length=100, null=True, blank=True, verbose_name="To‘lov tranzaksiyasining  ID raqami")
    billing_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="Hamkor billing tizimidagi tranzaksiyaning  ID raqami")
    sign = models.CharField(max_length=100, null=True, blank=True, verbose_name="MD5 HASH")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="To‘lov summasi")
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, verbose_name="Tranzaksiya ID")
    status = models.CharField(max_length=20, choices=[
        ("pending", "Kutilmoqda"),
        ("success", "Muvaffaqiyatli"),
        ("failed", "Muvaffaqiyatsiz")
    ], default="pending", verbose_name="Holat")
    payment_gateway = models.CharField(max_length=50, null=True, blank=True, verbose_name="To‘lov tizimi")
    receipt_url = models.URLField(null=True, blank=True, verbose_name="To‘lov chek havolasi")


    def __str__(self):
        return f"{self.student.full_name} - {self.amount} - {self.status}"

    class Meta:
        verbose_name = "To‘lov"
        verbose_name_plural = "To‘lovlar"


class MonthlyPayment(models.Model):
    price = models.PositiveIntegerField(default=1000, help_text="Oylik to‘lov summasi (so‘m)")

    def __str__(self):
        return f"Oylik to‘lov: {self.price} so‘m"

    class Meta:
        verbose_name = "Oylik to‘lov"
        verbose_name_plural = "Oylik to‘lov"



class SubscriptionPlan(models.Model):
    PLAN_CHOICES = (
        (1, '1 oylik'),
        (3, '3 oylik'),
        (6, '6 oylik'),
        (12, '12 oylik'),
    )

    months = models.PositiveIntegerField(
        choices=PLAN_CHOICES,
        verbose_name="Davomiylik (oy)"
    )
    discount_percent = models.PositiveIntegerField(
        default=0,
        verbose_name="Chegirma foizi"
    )
    price_per_month = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Oyiga narx"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Faolmi"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqti"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan vaqti"
    )

    def total_price(self):
        """Chegirmadan keyingi umumiy narx"""
        full_price = self.months * self.price_per_month
        discount_amount = (full_price * self.discount_percent) / 100
        return full_price - discount_amount

    def __str__(self):
        return f"{self.get_months_display()} (chegirma: {self.discount_percent}%)"

    class Meta:
        verbose_name = "Obuna rejasi"
        verbose_name_plural = "Obuna rejalar"