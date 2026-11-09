from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_payments', '0017_payment_plan'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptionsetting',
            name='default_tariff',
            field=models.CharField(
                choices=[('start', 'Start'), ('start_pro', 'Start Pro')],
                default='start_pro',
                max_length=20,
                verbose_name='Sinov muddatidagi tarif (default)',
            ),
        ),
    ]
