import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_tutor', '0009_tutorgroup'),
        ('app_user', '0021_alter_parentstudentrelation_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TutorGroupInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'Kutilmoqda'), ('accepted', 'Qabul qilingan'), ('rejected', 'Rad etilgan'), ('cancelled', 'Bekor qilingan')], default='pending', max_length=10, verbose_name='Holat')),
                ('message', models.TextField(blank=True, null=True, verbose_name='Xabar')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Yuborilgan sana')),
                ('responded_at', models.DateTimeField(blank=True, null=True, verbose_name='Javob berilgan sana')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='app_tutor.tutorgroup', verbose_name='Guruh')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tutor_group_invitations', to='app_user.student', verbose_name="O'quvchi")),
                ('tutor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_invitations', to='app_user.tutor', verbose_name="Taklif qilgan o'qituvchi")),
            ],
            options={
                'verbose_name': 'Guruhga taklif',
                'verbose_name_plural': 'Guruhga takliflar',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='tutorgroupinvitation',
            constraint=models.UniqueConstraint(
                condition=models.Q(('status', 'pending')),
                fields=('group', 'student'),
                name='unique_pending_tutor_group_invitation'
            ),
        ),
    ]
