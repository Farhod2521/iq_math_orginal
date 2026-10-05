import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_student', '0018_topicprogress_result'),
        ('app_user', '0021_alter_parentstudentrelation_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Achievement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title_uz', models.CharField(max_length=120, verbose_name='Nomi (uz)')),
                ('title_ru', models.CharField(max_length=120, verbose_name='Nomi (ru)')),
                ('description_uz', models.CharField(blank=True, default='', max_length=255, verbose_name='Tavsif (uz)')),
                ('description_ru', models.CharField(blank=True, default='', max_length=255, verbose_name='Tavsif (ru)')),
                ('image', models.ImageField(upload_to='achievements/', verbose_name='Rasm (badge)')),
                ('condition_type', models.CharField(choices=[('topics_completed', "O'zlashtirilgan mavzular soni (ball ≥ 80)"), ('correct_answers', "To'g'ri yechilgan savollar soni"), ('streak_days', 'Ketma-ket faol kunlar (seriya)'), ('active_days_30', "So'nggi 30 kundagi faol kunlar soni"), ('subject_mastery', "Tanlangan fan bo'yicha o'zlashtirish foizi"), ('diagnostics_taken', 'Topshirilgan diagnostikalar soni'), ('diagnostic_score', 'Diagnostikadagi eng yuqori natija (%)'), ('total_score', "To'plangan ballar"), ('total_coins', "To'plangan tangalar")], max_length=30, verbose_name='Shart turi')),
                ('threshold', models.PositiveIntegerField(default=1, help_text="Ko'rsatkich shu qiymatga yetganda yutuq beriladi (foizli shartlarda 0–100).", verbose_name='Qiymat')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Tartib')),
                ('is_active', models.BooleanField(default=True, verbose_name='Faol')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('subject', models.ForeignKey(blank=True, help_text='Faqat "fan bo\'yicha o\'zlashtirish" sharti uchun.', null=True, on_delete=django.db.models.deletion.CASCADE, to='app_user.subject', verbose_name='Fan')),
            ],
            options={
                'verbose_name': 'Yutuq',
                'verbose_name_plural': 'Yutuqlar',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='StudentAchievement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('awarded_at', models.DateTimeField(auto_now_add=True, verbose_name='Olingan vaqti')),
                ('achievement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='awards', to='app_student.achievement', verbose_name='Yutuq')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='achievements', to='app_user.student', verbose_name="O'quvchi")),
            ],
            options={
                'verbose_name': "O'quvchi yutug'i",
                'verbose_name_plural': "O'quvchilar yutuqlari",
                'ordering': ['-awarded_at'],
                'unique_together': {('student', 'achievement')},
            },
        ),
    ]
