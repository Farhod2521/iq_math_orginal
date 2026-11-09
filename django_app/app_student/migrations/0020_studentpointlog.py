import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_student', '0019_achievement_studentachievement'),
        ('app_user', '0021_alter_parentstudentrelation_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentPointLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(choices=[('daily_login', 'Kundalik kirish mukofoti')], max_length=30, verbose_name='Manba')),
                ('points', models.PositiveIntegerField(verbose_name='Ball')),
                ('date', models.DateField(verbose_name='Sana (mahalliy)')),
                ('streak_day', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Ketma-ketlik kuni')),
                ('score_after', models.PositiveIntegerField(default=0, verbose_name='Balans (keyin)')),
                ('comment', models.CharField(blank=True, default='', max_length=255, verbose_name='Izoh')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Vaqti')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='point_logs', to='app_user.student', verbose_name="O'quvchi")),
            ],
            options={
                'verbose_name': 'Ball tarixi (bonuslar)',
                'verbose_name_plural': 'Ball tarixi (bonuslar)',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['student', 'source', '-date'], name='student_point_log_idx')],
                'constraints': [models.UniqueConstraint(fields=('student', 'source', 'date'), name='uniq_student_point_source_date')],
            },
        ),
    ]
