from django.db import models
from django_app.app_user.models import Student, Tutor
from django_app.app_management.models import  Coupon_Tutor_Student, Referral_Tutor_Student


class TutorCouponTransaction(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='used_coupons', verbose_name="Kuponni ishlatgan student")
    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='coupon_transactions', verbose_name="Kupon egasi (Tutor)")
    coupon = models.ForeignKey(Coupon_Tutor_Student, on_delete=models.CASCADE, related_name='transactions', verbose_name="Kupon kodi")
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="To‘lov summasi")
    cashback_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="O'qtuvchiga berilgan keshbek")
    used_at = models.DateTimeField(auto_now_add=True, verbose_name="Kupon ishlatilgan sana")

    class Meta:
        verbose_name = "Tutor kupon tranzaksiyasi"
        verbose_name_plural = "Tutor kupon tranzaksiyalari"

    def __str__(self):
        return f"{self.student} → {self.coupon.code} ({self.payment_amount} so‘m)"
    
class TutorReferralTransaction(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='used_referrals',
        verbose_name="Referal link orqali kelgan student"
    )
    tutor = models.ForeignKey(
        Tutor,
        on_delete=models.CASCADE,
        related_name='referral_transactions',
        verbose_name="Referal link egasi (Tutor)"
    )
    payment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="To‘lov summasi"
    )

    bonus_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="O‘qituvchiga berilgan bonus"
    )
    used_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Referal ishlatilgan sana"
    )

    class Meta:
        verbose_name = "Tutor referal tranzaksiyasi"
        verbose_name_plural = "Tutor referal tranzaksiyalari"

    def __str__(self):
        return f"{self.student} → ({self.payment_amount} so‘m)"
    



class TutorWithdrawal(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('approved', 'Tasdiqlangan'),
        ('rejected', 'Rad etilgan'),
    )

    tutor = models.ForeignKey(
        Tutor,
        on_delete=models.CASCADE,
        related_name='withdrawals',
        verbose_name="O‘qituvchi"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="So‘ralgan summa")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="So‘ralgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")

    class Meta:
        verbose_name = "O‘qituvchi yechib olish"
        verbose_name_plural = "O‘qituvchi yechib olishlar"

    def __str__(self):
        return f"{self.tutor.full_name} - {self.amount} so‘m ({self.status})"



class WithdrawalLimitSettings(models.Model):
    min_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Minimal yechib olish summasi"
    )
    max_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Maksimal yechib olish summasi"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Yangilangan vaqt"
    )

    class Meta:
        verbose_name = "Yechib olish sozlamalari"
        verbose_name_plural = "Yechib olish sozlamalari"

    def __str__(self):
        return f"Min: {self.min_amount} | Max: {self.max_amount}"