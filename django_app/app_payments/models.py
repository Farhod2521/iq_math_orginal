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