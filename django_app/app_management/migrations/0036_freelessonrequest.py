from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_management", "0035_sitevisit"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FreeLessonRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("parent_name", models.CharField(max_length=150, verbose_name="Ota-ona ismi")),
                ("phone", models.CharField(db_index=True, max_length=20, verbose_name="Telefon")),
                ("class_num", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Farzand sinfi")),
                ("status", models.CharField(choices=[("new", "Yangi"), ("contacted", "Bog'lanildi"), ("enrolled", "Ro'yxatdan o'tdi"), ("rejected", "Rad etildi")], db_index=True, default="new", max_length=12, verbose_name="Holati")),
                ("note", models.TextField(blank=True, default="", verbose_name="Izoh")),
                ("source", models.CharField(blank=True, default="home_banner", max_length=30, verbose_name="Manba")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Yuborilgan vaqti")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("handled_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="handled_free_lessons", to=settings.AUTH_USER_MODEL, verbose_name="Ishlov bergan")),
            ],
            options={
                "verbose_name": "Bepul darsga ariza",
                "verbose_name_plural": "Bepul darsga arizalar",
                "ordering": ["-created_at"],
            },
        ),
    ]
