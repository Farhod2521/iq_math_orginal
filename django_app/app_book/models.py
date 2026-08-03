from django.db import models
from django_app.app_user.models import User


class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nomi")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['name']


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nomi")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Teg"
        verbose_name_plural = "Teglar"
        ordering = ['name']


class Book(models.Model):
    STATUS_CHOICES = [
        ('active', 'Faol'),
        ('inactive', 'Nofaol'),
        ('draft', 'Qoralama'),
    ]

    name = models.CharField(max_length=500, verbose_name="Nomi")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='books',
        verbose_name="Kategoriya"
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='books',
        verbose_name="Teglar"
    )
    file = models.FileField(upload_to='books/files/', null=True, blank=True, verbose_name="Fayl (PDF)")
    cover_image = models.ImageField(upload_to='books/covers/', null=True, blank=True, verbose_name="Muqova rasmi")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Narxi")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Holat"
    )
    is_offline = models.BooleanField(
        null=True, blank=True, default=False,
        verbose_name="Oflayn kitobmi (yetkazib berish mumkin)"
    )
    for_student = models.BooleanField(default=False, verbose_name="Student uchun")
    for_teacher = models.BooleanField(default=False, verbose_name="O'qituvchi uchun")
    quantity = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Ombordagi soni"
    )
    date = models.DateField(verbose_name="Sana")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Kitob"
        verbose_name_plural = "Kitoblar"
        ordering = ['-created_at']


class BookPurchase(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('som',   "So'm"),
        ('coin',  "Tanga"),
        ('score', "Ball"),
        ('card',  "Karta (onlayn to'lov)"),
    ]

    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='book_purchases', verbose_name="Foydalanuvchi")
    book           = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='purchases', verbose_name="Kitob")
    quantity       = models.PositiveIntegerField(default=1, verbose_name="Soni")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, verbose_name="To'lov turi")
    paid_amount    = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="To'langan jami miqdor")
    purchased_at   = models.DateTimeField(auto_now_add=True, verbose_name="Sotib olingan vaqt")

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.phone} — {self.book.name} ({self.payment_method})"

    class Meta:
        verbose_name = "Kitob xaridi"
        verbose_name_plural = "Kitob xaridlari"
        unique_together = ('user', 'book')
        ordering = ['-purchased_at']


class BookPayment(models.Model):
    """
    Kitob uchun onlayn (Multicard) to'lov.

    Foydalanuvchining tanga/ball/so'm balansi yetmagan holatda kitob shu model
    orqali karta bilan sotib olinadi:
        1. `BookInitiatePaymentAPIView` invoys yaratadi  → status="pending"
        2. Foydalanuvchi to'lov sahifasiga yo'naltiriladi (checkout_url)
        3. Multicard callback yuboradi → status="success" va `BookPurchase` yaratiladi
    """
    STATUS_CHOICES = [
        ('pending', "Kutilmoqda"),
        ('success', "Muvaffaqiyatli"),
        ('failed',  "Muvaffaqiyatsiz"),
    ]

    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='book_payments', verbose_name="Foydalanuvchi")
    book           = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='payments', verbose_name="Kitob")
    purchase       = models.OneToOneField(
        'BookPurchase', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payment', verbose_name="Yaratilgan xarid"
    )

    quantity       = models.PositiveIntegerField(default=1, verbose_name="Soni")
    unit_price     = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Dona narxi (so'm)")
    amount         = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="To'lov summasi (so'm)")

    transaction_id = models.CharField(max_length=100, unique=True, verbose_name="Tranzaksiya ID (invoice_id)")
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Holat")
    payment_gateway = models.CharField(max_length=50, default='multicard', verbose_name="To'lov tizimi")
    checkout_url   = models.URLField(max_length=500, null=True, blank=True, verbose_name="To'lov sahifasi havolasi")

    # Multicard callback maydonlari
    store_id       = models.CharField(max_length=100, null=True, blank=True, verbose_name="Multicard store ID")
    invoice_uuid   = models.CharField(max_length=100, null=True, blank=True, verbose_name="Invoys UUID")
    uuid           = models.CharField(max_length=100, null=True, blank=True, verbose_name="Tranzaksiya UUID")
    billing_id     = models.CharField(max_length=100, null=True, blank=True, verbose_name="Billing ID")
    sign           = models.CharField(max_length=100, null=True, blank=True, verbose_name="MD5 HASH")
    receipt_url    = models.URLField(null=True, blank=True, verbose_name="Chek havolasi")

    # Oflayn kitob uchun yetkazib berish ma'lumotlari (to'lov tasdiqlangach ishlatiladi)
    delivery_address = models.TextField(null=True, blank=True, verbose_name="Yetkazib berish manzili")
    delivery_phone   = models.CharField(max_length=20, null=True, blank=True, verbose_name="Telefon raqam")

    payment_date   = models.DateTimeField(null=True, blank=True, verbose_name="To'lov sanasi")
    created_at     = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at     = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    def __str__(self):
        return f"{self.user.phone} — {self.book.name} — {self.amount} ({self.status})"

    class Meta:
        verbose_name = "Kitob to'lovi"
        verbose_name_plural = "Kitob to'lovlari"
        ordering = ['-created_at']


class OfflineBookOrder(models.Model):
    """Oflayn kitob buyurtmasi — yetkazib berish holati shu yerda saqlanadi."""
    STATUS_CHOICES = [
        ('new',        "Yangi buyurtma"),
        ('seen',       "Admin ko'rdi"),
        ('preparing',  "Tayyorlanmoqda"),
        ('delivering', "Yetkazilmoqda"),
        ('delivered',  "Yetkazib berildi"),
    ]

    purchase         = models.OneToOneField(
        BookPurchase, on_delete=models.CASCADE,
        related_name='offline_order', verbose_name="Xarid"
    )
    delivery_status  = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='new', verbose_name="Yetkazib berish holati"
    )
    delivery_address = models.TextField(verbose_name="Yetkazib berish manzili")
    phone            = models.CharField(max_length=20, verbose_name="Telefon raqam")
    admin_note       = models.TextField(blank=True, null=True, verbose_name="Admin izohi")
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.purchase.user.phone} — {self.purchase.book.name} [{self.delivery_status}]"

    class Meta:
        verbose_name = "Oflayn kitob buyurtmasi"
        verbose_name_plural = "Oflayn kitob buyurtmalari"
        ordering = ['-created_at']
