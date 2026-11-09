"""Eski yozuvlarni hamyon tarixiga (StudentWalletLog) ko'chirish.

Xotirani tejash uchun: darslar (StudentScoreLog) bazaning o'zida GROUP BY bilan jamlanadi,
hamma joyda iterator(chunk_size) va bulk_create(BATCH) — Python xotirasida hech qachon
BATCH tadan ko'p obyekt turmaydi.

Eski yozuvlarning ko'pchiligida "qoldiq" saqlanmagan — balance_after bo'sh qoladi (frontendda "—").
Bellashuv g'alabalari avval loglanmagani uchun ko'chirilmaydi.
Migratsiya bitta tranzaksiyada: to'xtab qolsa hammasi bekor bo'ladi, qayta ishga tushirish xavfsiz.
Sayt yangi kod bilan ishlab, jadvalga yozuv tushib ulgurgan bo'lsa — faqat birinchi yangi yozuvdan
oldingi eski yozuvlar ko'chiriladi (dublikat bo'lmaydi).
"""
from django.db import migrations
from django.db.models import Count, Min
from django.db.models.functions import TruncMinute

BATCH = 1000
CHUNK = 2000


def backfill(apps, schema_editor):
    WalletLog = apps.get_model('app_student', 'StudentWalletLog')
    # Yangi kod yozgan birinchi yozuv vaqti — undan keyingilar allaqachon jadvalda
    cutoff = WalletLog.objects.order_by('created_at').values_list('created_at', flat=True).first()

    def before(qs, field):
        return qs.filter(**{f'{field}__lt': cutoff}) if cutoff else qs

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

    def flush():
        if rows:
            WalletLog.objects.bulk_create(rows, batch_size=BATCH)
            rows.clear()

    def add(student_id, currency, amount, source, text, created_at, balance_after=None, ref=""):
        if not student_id or not amount or created_at is None:
            return
        rows.append(WalletLog(
            student_id=student_id, currency=currency, source=source, amount=int(amount),
            balance_after=balance_after, description=(text or "")[:255], ref=(ref or "")[:50],
            created_at=created_at,
        ))
        if len(rows) >= BATCH:
            flush()

    # Gol (kundalik kirish, haftalik test)
    for log in before(StudentPointLog.objects.order_by(), 'created_at').iterator(chunk_size=CHUNK):
        add(log.student_id, 'gol', log.gol, log.source, log.comment, log.created_at, log.gol_after, f"gol:{log.id}")

    # Darslar: har savol +1 tanga/ball — (o'quvchi, tur, mavzu, daqiqa) bo'yicha bazada jamlanadi
    lessons = (
        before(StudentScoreLog.objects.order_by(), 'awarded_at')
        .annotate(minute=TruncMinute('awarded_at'))
        .values('student_score__student_id', 'award_type', 'question__topic_id', 'question__topic__name', 'minute')
        .annotate(cnt=Count('id'), at=Min('awarded_at'))
    )
    for item in lessons.iterator(chunk_size=CHUNK):
        topic_id = item['question__topic_id']
        name = item['question__topic__name'] or ''
        lesson = f"“{name}” mavzusi" if name else "Mashq"
        add(item['student_score__student_id'], item['award_type'], item['cnt'], 'lesson',
            f"{lesson}: {item['cnt']} ta yangi to'g'ri javob", item['at'],
            ref=f"topic:{topic_id}" if topic_id else "")

    # Almashtirishlar
    labels = {'score': 'ball', 'coin': 'tanga', 'som': "so'm"}
    for item in before(ConversionHistory.objects.filter(status='approved').order_by(), 'created_at').iterator(chunk_size=CHUNK):
        try:
            source_cur, target_cur = item.conversion_type.lower().split('_to_')
        except ValueError:
            continue
        text = f"{item.amount_from} {labels.get(source_cur, source_cur)} → {item.amount_to} {labels.get(target_cur, target_cur)}"
        add(item.student_id, source_cur, -item.amount_from, 'convert', text, item.created_at, ref=f"conv:{item.id}")
        add(item.student_id, target_cur, item.amount_to, 'convert', text, item.created_at,
            item.som_after if target_cur == 'som' else None, f"conv:{item.id}")

    # Do'kon
    exchanges = before(ProductExchange.objects.order_by(), 'created_at').values('id', 'student_id', 'used_coin', 'created_at', 'product__name')
    for item in exchanges.iterator(chunk_size=CHUNK):
        add(item['student_id'], 'coin', -item['used_coin'], 'shop', f"“{item['product__name']}” sotib olindi",
            item['created_at'], ref=f"exchange:{item['id']}")

    # So'm o'tkazmalari
    transfers = before(SomTransferLog.objects.filter(is_confirmed=True).order_by(), 'created_at').values(
        'id', 'sender_id', 'receiver_id', 'amount', 'confirmed_at', 'created_at',
        'sender__full_name', 'receiver__full_name',
    )
    for item in transfers.iterator(chunk_size=CHUNK):
        at = item['confirmed_at'] or item['created_at']
        add(item['sender_id'], 'som', -item['amount'], 'transfer', f"{item['receiver__full_name']}ga o'tkazildi", at,
            ref=f"transfer:{item['id']}")
        add(item['receiver_id'], 'som', item['amount'], 'transfer', f"{item['sender__full_name']}dan qabul qilindi", at,
            ref=f"transfer:{item['id']}")

    # O'qituvchi rag'batlari va jarimalar
    for item in before(TeacherRewardLog.objects.filter(reward_type__in=['score', 'coin']).order_by(), 'created_at').iterator(chunk_size=CHUNK):
        text = f"O'qituvchi rag'bati: {item.reason}" if item.reason else "O'qituvchi rag'bati"
        add(item.student_id, item.reward_type, item.amount, 'reward', text, item.created_at, ref=f"reward:{item.id}")
    for item in before(TeacherFineLog.objects.order_by(), 'created_at').iterator(chunk_size=CHUNK):
        add(item.student_id, item.fine_type, -item.amount, 'fine', f"Jarima: {item.reason}", item.created_at,
            ref=f"fine:{item.id}")

    # Kitoblar (balans bilan sotib olingan)
    books = before(BookPurchase.objects.filter(payment_method__in=['som', 'coin', 'score']).order_by(), 'purchased_at').values(
        'id', 'user_id', 'payment_method', 'paid_amount', 'purchased_at', 'book__name',
    )
    for item in books.iterator(chunk_size=CHUNK):
        student_id = Student.objects.filter(user_id=item['user_id']).values_list('id', flat=True).first()
        add(student_id, item['payment_method'], -int(item['paid_amount']), 'book',
            f"“{item['book__name']}” kitobi sotib olindi", item['purchased_at'], ref=f"book:{item['id']}")

    flush()


class Migration(migrations.Migration):
    dependencies = [
        ('app_student', '0022_studentwalletlog'),
        ('app_teacher', '0012_questionimagebackup'),
        ('app_book', '0007_bookpayment_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
