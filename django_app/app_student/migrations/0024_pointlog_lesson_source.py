from django.db import migrations, models


class Migration(migrations.Migration):
    """Gol tarixiga yangi manba: mavzu misollari (har bir yangi yechilgan misol uchun 1 gol)."""

    dependencies = [
        ("app_student", "0023_wallet_backfill"),
    ]

    operations = [
        migrations.AlterField(
            model_name="studentpointlog",
            name="source",
            field=models.CharField(
                choices=[
                    ("daily_login", "Kundalik kirish"),
                    ("weekly_test", "Haftalik test"),
                    ("lesson", "Mavzu misollari"),
                ],
                max_length=30,
                verbose_name="Manba",
            ),
        ),
    ]
