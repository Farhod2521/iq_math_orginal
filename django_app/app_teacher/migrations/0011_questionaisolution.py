from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("app_teacher", "0010_alter_compositesubquestion_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuestionAISolution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("lang", models.CharField(choices=[("uz", "O'zbekcha"), ("ru", "Ruscha")], default="uz", max_length=2)),
                ("data", models.JSONField(verbose_name="Yechim (JSON)")),
                ("ai_model", models.CharField(blank=True, default="", max_length=100, verbose_name="AI model")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_solutions",
                        to="app_teacher.question",
                    ),
                ),
            ],
            options={
                "verbose_name": "AI yechim",
                "verbose_name_plural": "AI yechimlar",
                "unique_together": {("question", "lang")},
            },
        ),
    ]
