import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_tutor', '0008_alter_tutorwithdrawal_options_and_more'),
        ('app_user', '0021_alter_parentstudentrelation_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TutorGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Guruh nomi')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Izoh')),
                ('is_active', models.BooleanField(default=True, verbose_name='Faolmi')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan sana')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Yangilangan sana')),
                ('students', models.ManyToManyField(blank=True, related_name='tutor_groups', to='app_user.student', verbose_name="O'quvchilar")),
                ('tutor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tutor_groups', to='app_user.tutor', verbose_name="O'qituvchi")),
            ],
            options={
                'verbose_name': 'Tutor guruhi',
                'verbose_name_plural': 'Tutor guruhlari',
                'ordering': ['-created_at'],
                'unique_together': {('tutor', 'name')},
            },
        ),
    ]
