import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_book', '0006_offlinebookorder'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookpurchase',
            name='payment_method',
            field=models.CharField(
                choices=[('som', "So'm"), ('coin', 'Tanga'), ('score', 'Ball'), ('card', "Karta (onlayn to'lov)")],
                max_length=10,
                verbose_name="To'lov turi",
            ),
        ),
        migrations.CreateModel(
            name='BookPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Soni')),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=14, verbose_name="Dona narxi (so'm)")),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14, verbose_name="To'lov summasi (so'm)")),
                ('transaction_id', models.CharField(max_length=100, unique=True, verbose_name='Tranzaksiya ID (invoice_id)')),
                ('status', models.CharField(choices=[('pending', 'Kutilmoqda'), ('success', 'Muvaffaqiyatli'), ('failed', 'Muvaffaqiyatsiz')], default='pending', max_length=20, verbose_name='Holat')),
                ('payment_gateway', models.CharField(default='multicard', max_length=50, verbose_name="To'lov tizimi")),
                ('checkout_url', models.URLField(blank=True, max_length=500, null=True, verbose_name="To'lov sahifasi havolasi")),
                ('store_id', models.CharField(blank=True, max_length=100, null=True, verbose_name='Multicard store ID')),
                ('invoice_uuid', models.CharField(blank=True, max_length=100, null=True, verbose_name='Invoys UUID')),
                ('uuid', models.CharField(blank=True, max_length=100, null=True, verbose_name='Tranzaksiya UUID')),
                ('billing_id', models.CharField(blank=True, max_length=100, null=True, verbose_name='Billing ID')),
                ('sign', models.CharField(blank=True, max_length=100, null=True, verbose_name='MD5 HASH')),
                ('receipt_url', models.URLField(blank=True, null=True, verbose_name='Chek havolasi')),
                ('delivery_address', models.TextField(blank=True, null=True, verbose_name='Yetkazib berish manzili')),
                ('delivery_phone', models.CharField(blank=True, max_length=20, null=True, verbose_name='Telefon raqam')),
                ('payment_date', models.DateTimeField(blank=True, null=True, verbose_name="To'lov sanasi")),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan sana')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Yangilangan sana')),
                ('book', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='app_book.book', verbose_name='Kitob')),
                ('purchase', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment', to='app_book.bookpurchase', verbose_name='Yaratilgan xarid')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='book_payments', to=settings.AUTH_USER_MODEL, verbose_name='Foydalanuvchi')),
            ],
            options={
                'verbose_name': "Kitob to'lovi",
                'verbose_name_plural': "Kitob to'lovlari",
                'ordering': ['-created_at'],
            },
        ),
    ]
