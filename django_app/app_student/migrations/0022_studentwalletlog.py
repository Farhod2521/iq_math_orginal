"""Hamyon tarixi (StudentWalletLog): ball, tanga, so'm va gol bo'yicha barcha kirim/chiqimlar.

Eski yozuvlar mavjud loglardan ko'chiriladi. Ularning ko'pchiligida "qoldiq" saqlanmagan —
balance_after bo'sh qoladi (frontendda "—"). Bellashuv g'alabalari avval loglanmagani uchun ko'chirilmaydi.
"""
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

BATCH = 1000


def backfill(apps, schema_editor):
    WalletLog = apps.get_model('app_student', 'StudentWalletLog')
    StudentPointLog = apps.get_model('app_student', 'StudentPointLog')
    StudentScoreLog = apps.get_model('app_student', 'StudentScoreLog')
    ConversionHistory = apps.get_model('app_student', 'ConversionHistory')
    ProductExchange = apps.get_model('app_student', 'ProductExchange')
    SomTransferLog = apps.get_model('app_student', 'SomTransferLog')
    TeacherRewardLog = apps.get_model('app_teacher', 'TeacherRewardLog')
    TeacherFineLog = apps.get_model('app_teacher', 'TeacherFineLog')
    BookPurchase = apps.get_model('app_book', 'BookPurchase')
    Student = apps.get_model('app_user', 'Student')

    rows = []

    def add(student_id, currency, amount, source, text, created_at, balance_after=None, ref=""):
        if not student_id or not amount:
            return
        rows.append(WalletLog(
            student_id=student_id, currency=currency, source=source, amount=int(amount),
            balance_after=balance_after, description=(text or "")[:255], ref=ref[:50], created_at=created_at,
        ))
        if len(rows) >= BATCH:
            WalletLog.objects.bulk_create(rows)
            rows.clear()

    # Gol (kundalik kirish, haftalik test)
    for log in StudentPointLog.objects.all().iterator():
        add(log.student_id, 'gol', log.gol, log.source, log.comment, log.created_at, log.gol_after, f"gol:{log.id}")

    # Darslar: har savol +1 tanga/ball — bir topshiriq (o'quvchi, tur, mavzu, daqiqa) bitta yozuvga jamlanadi
    groups = {}
    logs = (
        StudentScoreLog.objects.select_related('student_score', 'question__topic')
        .order_by('awarded_at').iterator()
    )
    for log in logs:
        topic = log.question.topic if log.question_id else None
        key = (
            log.student_score.student_id, log.award_type, topic.id if topic else None,
            log.awarded_at.replace(second=0, microsecond=0),
        )
        group = groups.setdefault(key, {'count': 0, 'at': log.awarded_at, 'topic': topic.name if topic else ''})
        group['count'] += 1
    for (student_id, award_type, topic_id, _minute), group in groups.items():
        lesson = f"“{group['topic']}” mavzusi" if group['topic'] else "Mashq"
        add(student_id, award_type, group['count'], 'lesson', f"{lesson}: {group['count']} ta yangi to'g'ri javob",
            group['at'], ref=f"topic:{topic_id}" if topic_id else "")

    # Almashtirishlar
    labels = {'score': 'ball', 'coin': 'tanga', 'som': "so'm"}
    for item in ConversionHistory.objects.filter(status='approved').iterator():
        source_cur, target_cur = item.conversion_type.lower().split('_to_')
        text = f"{item.amount_from} {labels[source_cur]} → {item.amount_to} {labels[target_cur]}"
        add(item.student_id, source_cur, -item.amount_from, 'convert', text, item.created_at, ref=f"conv:{item.id}")
        add(item.student_id, target_cur, item.amount_to, 'convert', text, item.created_at,
            item.som_after if target_cur == 'som' else None, f"conv:{item.id}")

    # Do'kon
    for item in ProductExchange.objects.select_related('product').iterator():
        add(item.student_id, 'coin', -item.used_coin, 'shop', f"“{item.product.name}” sotib olindi",
            item.created_at, ref=f"exchange:{item.id}")

    # So'm o'tkazmalari
    for item in SomTransferLog.objects.filter(is_confirmed=True).select_related('sender', 'receiver').iterator():
        at = item.confirmed_at or item.created_at
        add(item.sender_id, 'som', -item.amount, 'transfer', f"{item.receiver.full_name}ga o'tkazildi", at,
            ref=f"transfer:{item.id}")
        add(item.receiver_id, 'som', item.amount, 'transfer', f"{item.sender.full_name}dan qabul qilindi", at,
            ref=f"transfer:{item.id}")

    # O'qituvchi rag'batlari va jarimalar
    for item in TeacherRewardLog.objects.filter(reward_type__in=['score', 'coin']).iterator():
        text = f"O'qituvchi rag'bati: {item.reason}" if item.reason else "O'qituvchi rag'bati"
        add(item.student_id, item.reward_type, item.amount, 'reward', text, item.created_at, ref=f"reward:{item.id}")
    for item in TeacherFineLog.objects.iterator():
        add(item.student_id, item.fine_type, -item.amount, 'fine', f"Jarima: {item.reason}", item.created_at,
            ref=f"fine:{item.id}")

    # Kitoblar (balans bilan sotib olingan)
    student_by_user = dict(Student.objects.values_list('user_id', 'id'))
    for item in BookPurchase.objects.filter(payment_method__in=['som', 'coin', 'score']).select_related('book').iterator():
        add(student_by_user.get(item.user_id), item.payment_method, -int(item.paid_amount), 'book',
            f"“{item.book.name}” kitobi sotib olindi", item.purchased_at, ref=f"book:{item.id}")

    if rows:
        WalletLog.objects.bulk_create(rows)


class Migration(migrations.Migration):

    dependencies = [
        ('app_student', '0021_gol'),
        ('app_teacher', '0012_questionimagebackup'),
        ('app_book', '0007_bookpayment_and_more'),
        ('app_user', '0021_alter_parentstudentrelation_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentWalletLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('currency', models.CharField(choices=[('score', 'Ball'), ('coin', 'Tanga'), ('som', "So'm"), ('gol', 'Gol')], max_length=10, verbose_name='Turi')),
                ('source', models.CharField(choices=[('daily_login', 'Kundalik kirish'), ('lesson', 'Dars'), ('weekly_test', 'Haftalik test'), ('battle', "O'yin"), ('reward', "Rag'bat"), ('fine', 'Jarima'), ('convert', 'Almashtirish'), ('shop', "Do'kon"), ('book', 'Kitob'), ('transfer', "O'tkazma"), ('other', 'Boshqa')], max_length=20, verbose_name="Bo'lim (manba)")),
                ('amount', models.IntegerField(verbose_name='Miqdor')),
                ('balance_after', models.IntegerField(blank=True, null=True, verbose_name='Qoldiq')),
                ('description', models.CharField(blank=True, default='', max_length=255, verbose_name='Tavsif')),
                ('ref', models.CharField(blank=True, default='', max_length=50, verbose_name="Bog'liq yozuv")),
                ('created_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now, verbose_name='Vaqti')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wallet_logs', to='app_user.student', verbose_name="O'quvchi")),
            ],
            options={
                'verbose_name': 'Hamyon tarixi',
                'verbose_name_plural': 'Hamyon tarixi',
                'ordering': ['-created_at', '-id'],
                'indexes': [models.Index(fields=['student', 'currency', '-created_at'], name='student_wallet_log_idx')],
            },
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
