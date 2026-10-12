from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app_management', '0034_certificatesettings'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('visitor_id', models.CharField(db_index=True, max_length=64, verbose_name='Tashrifchi ID')),
                ('session_id', models.CharField(db_index=True, max_length=64, verbose_name='Sessiya ID')),
                ('path', models.CharField(db_index=True, max_length=300, verbose_name='Sahifa')),
                ('referrer', models.CharField(blank=True, default='', max_length=500, verbose_name='Qayerdan kelgan')),
                ('source', models.CharField(choices=[('direct', "To'g'ridan-to'g'ri"), ('search', 'Qidiruv tizimlari'), ('social', 'Ijtimoiy tarmoqlar'), ('telegram', 'Telegram'), ('referral', 'Boshqa saytlar')], db_index=True, default='direct', max_length=10, verbose_name='Manba')),
                ('device_type', models.CharField(choices=[('mobile', 'Telefon'), ('desktop', 'Kompyuter'), ('tablet', 'Planshet'), ('other', 'Boshqa')], default='other', max_length=10, verbose_name='Qurilma turi')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('country_code', models.CharField(blank=True, db_index=True, default='', max_length=2, verbose_name='Davlat kodi')),
                ('country_name', models.CharField(blank=True, default='', max_length=100, verbose_name='Davlat')),
                ('region', models.CharField(blank=True, db_index=True, default='', max_length=30, verbose_name='Viloyat')),
                ('geo_resolved', models.BooleanField(db_index=True, default=False)),
                ('is_entry', models.BooleanField(default=False, verbose_name='Sessiyaning birinchi sahifasi')),
                ('is_new_visitor', models.BooleanField(default=False, verbose_name='Yangi tashrifchi')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Vaqti')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='site_visits', to=settings.AUTH_USER_MODEL, verbose_name='Foydalanuvchi')),
            ],
            options={
                'verbose_name': 'Sayt tashrifi',
                'verbose_name_plural': 'Sayt tashriflari',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['created_at', 'visitor_id'], name='sitevisit_created_visitor')],
            },
        ),
    ]
