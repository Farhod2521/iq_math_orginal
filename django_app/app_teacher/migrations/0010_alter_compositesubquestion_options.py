from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app_teacher', '0009_alter_teacherproductexchange_options_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='compositesubquestion',
            options={
                'ordering': ['id'],
                'verbose_name': 'Kichik savol',
                'verbose_name_plural': 'Kichik savollar',
            },
        ),
    ]
