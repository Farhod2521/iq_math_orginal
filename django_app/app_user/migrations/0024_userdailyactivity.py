from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_user", "0023_user_avatar"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserDailyActivity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(db_index=True, verbose_name="Sana")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="daily_activity", to=settings.AUTH_USER_MODEL, verbose_name="Foydalanuvchi")),
            ],
            options={
                "verbose_name": "Kunlik faollik",
                "verbose_name_plural": "Kunlik faollik",
                "ordering": ["-date"],
                "unique_together": {("user", "date")},
            },
        ),
    ]
