from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_teacher", "0011_questionaisolution"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuestionImageBackup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("field", models.CharField(max_length=50, verbose_name="Maydon")),
                ("original", models.TextField(verbose_name="Asl matn (HTML)")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="image_backups",
                        to="app_teacher.question",
                    ),
                ),
            ],
            options={
                "verbose_name": "Rasm zaxirasi",
                "verbose_name_plural": "Rasm zaxiralari",
                "ordering": ["-created_at"],
            },
        ),
    ]
