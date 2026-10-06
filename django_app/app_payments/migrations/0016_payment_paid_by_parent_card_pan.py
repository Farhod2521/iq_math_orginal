from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app_payments', '0015_alter_subscription_is_paid_and_more'),
        ('app_user', '0022_userdevice'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='card_pan',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Karta raqami (yashirilgan)'),
        ),
        migrations.AddField(
            model_name='payment',
            name='paid_by_parent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='child_payments',
                to='app_user.parent',
                verbose_name="To'lagan ota-ona",
            ),
        ),
    ]
