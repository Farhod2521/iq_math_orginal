from django.db import models


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
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Narxi")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Holat"
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
