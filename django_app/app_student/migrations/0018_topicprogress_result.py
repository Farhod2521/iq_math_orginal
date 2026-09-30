from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_student', '0017_alter_chapterprogress_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='topicprogress',
            name='result',
            field=models.JSONField(blank=True, null=True, verbose_name="Urinishlar ma'lumoti"),
        ),
    ]
