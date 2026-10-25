from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_user", "0024_userdailyactivity"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserOnlineSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("started_at", models.DateTimeField(db_index=True, verbose_name="Kirgan vaqti")),
                ("last_seen_at", models.DateTimeField(verbose_name="Oxirgi faollik")),
                ("ended_at", models.DateTimeField(blank=True, null=True, verbose_name="Chiqqan vaqti")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="online_sessions", to=settings.AUTH_USER_MODEL, verbose_name="Foydalanuvchi")),
            ],
            options={
                "verbose_name": "Onlayn sessiya",
                "verbose_name_plural": "Onlayn sessiyalar",
                "ordering": ["-started_at"],
                "indexes": [models.Index(fields=["user", "-last_seen_at"], name="online_user_seen_idx")],
            },
        ),
    ]
