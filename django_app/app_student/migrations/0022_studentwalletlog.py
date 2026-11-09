"""Hamyon tarixi (StudentWalletLog) jadvali. Eski yozuvlarni ko'chirish — 0023_wallet_backfill."""
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('app_student', '0021_gol'),
        ('app_user', '0021_alter_parentstudentrelation_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentWalletLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('currency', models.CharField(choices=[('score', 'Ball'), ('coin', 'Tanga'), ('som', "So'm"), ('gol', 'Gol')], max_length=10, verbose_name='Turi')),
                ('source', models.CharField(choices=[('daily_login', 'Kundalik kirish'), ('lesson', 'Dars'), ('weekly_test', 'Haftalik test'), ('battle', "O'yin"), ('reward', "Rag'bat"), ('fine', 'Jarima'), ('convert', 'Almashtirish'), ('shop', "Do'kon"), ('book', 'Kitob'), ('transfer', "O'tkazma"), ('other', 'Boshqa')], max_length=20, verbose_name="Bo'lim (manba)")),
                ('amount', models.IntegerField(verbose_name='Miqdor')),
                ('balance_after', models.IntegerField(blank=True, null=True, verbose_name='Qoldiq')),
                ('description', models.CharField(blank=True, default='', max_length=255, verbose_name='Tavsif')),
                ('ref', models.CharField(blank=True, default='', max_length=50, verbose_name="Bog'liq yozuv")),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now, verbose_name='Vaqti')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wallet_logs', to='app_user.student', verbose_name="O'quvchi")),
            ],
            options={
                'verbose_name': 'Hamyon tarixi',
                'verbose_name_plural': 'Hamyon tarixi',
                'ordering': ['-created_at', '-id'],
                'indexes': [models.Index(fields=['student', 'currency', '-created_at'], name='student_wallet_log_idx')],
            },
        ),
    ]
