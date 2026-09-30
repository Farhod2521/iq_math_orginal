import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_user', '0021_alter_parentstudentrelation_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserDevice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('device_key', models.CharField(db_index=True, max_length=100, verbose_name='Qurilma kaliti')),
                ('device_name', models.CharField(blank=True, default='', max_length=255, verbose_name='Qurilma nomi')),
                ('device_type', models.CharField(choices=[('desktop', 'Kompyuter'), ('mobile', 'Telefon'), ('tablet', 'Planshet'), ('other', 'Boshqa')], default='other', max_length=10, verbose_name='Qurilma turi')),
                ('user_agent', models.TextField(blank=True, default='')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='Faol')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Kirgan vaqti')),
                ('last_used_at', models.DateTimeField(auto_now_add=True, verbose_name='Oxirgi faollik')),
                ('logged_out_at', models.DateTimeField(blank=True, null=True, verbose_name='Chiqarilgan vaqti')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='devices', to=settings.AUTH_USER_MODEL, verbose_name='Foydalanuvchi')),
            ],
            options={
                'verbose_name': 'Qurilma',
                'verbose_name_plural': 'Qurilmalar',
                'ordering': ['-last_used_at'],
            },
        ),
    ]
