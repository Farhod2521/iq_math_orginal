from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app_payments', '0016_payment_paid_by_parent_card_pan'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='plan',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='payments',
                to='app_payments.subscriptionplan',
                verbose_name='Tarif',
            ),
        ),
    ]
