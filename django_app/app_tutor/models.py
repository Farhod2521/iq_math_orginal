from django.db import models
from django.db.models import Q
from django_app.app_user.models import Student, Tutor
from django_app.app_management.models import  Coupon_Tutor_Student, Referral_Tutor_Student


class TutorCouponTransaction(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='used_coupons', verbose_name="Kuponni ishlatgan student")
    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='coupon_transactions', verbose_name="Kupon egasi (Tutor)")
    coupon = models.ForeignKey(Coupon_Tutor_Student, on_delete=models.CASCADE, related_name='transactions', verbose_name="Kupon kodi")
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="To'lov summasi")
    cashback_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="O'qtuvchiga berilgan keshbek")
    used_at = models.DateTimeField(auto_now_add=True, verbose_name="Kupon ishlatilgan sana")

    class Meta:
        verbose_name = "Tutor kupon tranzaksiyasi"
        verbose_name_plural = "Tutor kupon tranzaksiyalari"

    def __str__(self):
        return f"{self.student} → {self.coupon.code} ({self.payment_amount} so'm)"
    
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
        verbose_name="To'lov summasi"
    )

    bonus_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="O'qituvchiga berilgan bonus"
    )
    used_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Referal ishlatilgan sana"
    )

    class Meta:
        verbose_name = "Tutor referal tranzaksiyasi"
        verbose_name_plural = "Tutor referal tranzaksiyalari"

    def __str__(self):
        return f"{self.student} → ({self.payment_amount} so'm)"
    



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
        verbose_name="O'qituvchi"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="So'ralgan summa")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="So'ralgan vaqt")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan vaqt")

    class Meta:
        verbose_name = "O'qituvchi yechib olish"
        verbose_name_plural = "O'qituvchi yechib olishlar"

    def __str__(self):
        return f"{self.tutor.full_name} - {self.amount} so'm ({self.status})"



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


class TutorGroup(models.Model):
    """
    O'qituvchi (tutor) o'z promo/referal havolasi orqali qo'shgan o'quvchilarini
    ajratib qo'yadigan guruh. app_teacher.Group faqat Teacher uchun ishlaydi,
    shuning uchun tutor uchun alohida model.
    """
    tutor = models.ForeignKey(
        Tutor,
        on_delete=models.CASCADE,
        related_name='tutor_groups',
        verbose_name="O'qituvchi"
    )
    name = models.CharField(max_length=200, verbose_name="Guruh nomi")
    description = models.TextField(blank=True, null=True, verbose_name="Izoh")
    students = models.ManyToManyField(
        Student,
        related_name='tutor_groups',
        blank=True,
        verbose_name="O'quvchilar"
    )
    is_active = models.BooleanField(default=True, verbose_name="Faolmi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    class Meta:
        verbose_name = "Tutor guruhi"
        verbose_name_plural = "Tutor guruhlari"
        ordering = ['-created_at']
        unique_together = ('tutor', 'name')

    def __str__(self):
        return f"{self.name} - {self.tutor.full_name}"


class TutorGroupInvitation(models.Model):
    """
    O'qituvchi tizimdagi istalgan o'quvchini o'z guruhiga taklif qiladi.
    O'quvchi tizimga kirganda taklifni ko'radi va qabul qiladi yoki rad etadi.
    """
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Kutilmoqda'),
        (STATUS_ACCEPTED, 'Qabul qilingan'),
        (STATUS_REJECTED, 'Rad etilgan'),
        (STATUS_CANCELLED, 'Bekor qilingan'),
    )

    group = models.ForeignKey(
        TutorGroup, on_delete=models.CASCADE, related_name='invitations', verbose_name="Guruh"
    )
    tutor = models.ForeignKey(
        Tutor, on_delete=models.CASCADE, related_name='group_invitations', verbose_name="Taklif qilgan o'qituvchi"
    )
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='tutor_group_invitations', verbose_name="O'quvchi"
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="Holat"
    )
    message = models.TextField(blank=True, null=True, verbose_name="Xabar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yuborilgan sana")
    responded_at = models.DateTimeField(blank=True, null=True, verbose_name="Javob berilgan sana")

    class Meta:
        verbose_name = "Guruhga taklif"
        verbose_name_plural = "Guruhga takliflar"
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'student'],
                condition=Q(status='pending'),
                name='unique_pending_tutor_group_invitation'
            )
        ]

    def __str__(self):
        return f"{self.student.full_name} -> {self.group.name} ({self.status})"
