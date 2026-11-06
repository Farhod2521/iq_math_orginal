"""test_add.json dagi savollarni Liga testiga qo'shadi.

    python test_add.py                  (mahalliy baza)
    DJANGO_ENV=production python test_add.py   (serverda)

Qayta ishga tushirilsa, testda bor savollar ikkinchi marta qo'shilmaydi.
Fan JSON boshidagi "subject" dan olinadi, savolning o'z "subject" i bo'lsa o'sha ishlatiladi.
Fayl nomi "test" bilan boshlangani uchun Django testlari uni import qilishi mumkin:
shu sababli baza bilan ishlash faqat main() ichida.
"""
import html
import json
import os
import sys
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / 'test_add.json'


def to_html(text):
    """Mentor panelidagi kabi saqlanadi: "a < b" teg bo'lib qolmasin."""
    return html.escape(text, quote=False).replace('\n', '<br>')


def find_subject(grade, name):
    from django_app.app_user.models import Subject

    subjects = Subject.objects.filter(classes=grade, active=True)
    if name:
        subjects = subjects.filter(name__iexact=name)
    elif subjects.count() > 1:
        subjects = subjects.filter(name__icontains='matem') or subjects

    if subjects.count() != 1:
        names = ', '.join(Subject.objects.filter(classes=grade, active=True).values_list('name', flat=True))
        sys.exit(f'Fanni aniqlab bo\'lmadi. test_add.json dagi "subject" ga bittasini yozing: {names or "fan yoq"}')
    return subjects.get()


def find_test(season, grade, week):
    """Test yo'q bo'lsa, shu haftadagi boshqa sinf testining vaqti bilan qoralama yaratiladi."""
    from django_app.app_liga.models import LigaTest

    test = LigaTest.objects.filter(season=season, grade=grade, week_number=week).first()
    if test:
        return test

    sample = LigaTest.objects.filter(season=season, week_number=week).first()
    if not sample:
        sys.exit(f"{season} da {week}-hafta testi yo'q. Avval mentor panelida haftani yarating.")
    return LigaTest.objects.create(
        season=season, grade=grade, week_number=week, start_at=sample.start_at, end_at=sample.end_at,
        duration_minutes=sample.duration_minutes, question_count=sample.question_count,
    )


def add_questions(data):
    from django.db import transaction
    from rest_framework.exceptions import ValidationError

    from django_app.app_liga.models import LigaSeason
    from django_app.app_liga.serializers import AdminQuestionSerializer
    from django_app.app_user.models import Class

    season = LigaSeason.objects.filter(number=data['season']).first()
    grade = Class.objects.filter(name=data['grade']).first()
    if not season or not grade:
        sys.exit(f"{data['season']}-mavsum yoki {data['grade']}-sinf bazada topilmadi.")

    with transaction.atomic():
        test = find_test(season, grade, data['week'])
        if test.attempts.exists():
            sys.exit("O'quvchilar bu testni boshlagan: savol qo'shib bo'lmaydi.")

        subjects = {}
        existing = set(test.questions.values_list('question_text_uz', flat=True))
        order = test.questions.count()
        added = 0

        for number, item in enumerate(data['questions'], start=1):
            text = to_html(item['text'])
            if text in existing:
                continue
            name = item.get('subject') or data.get('subject')
            if name not in subjects:
                subjects[name] = find_subject(grade, name)
            order += 1
            serializer = AdminQuestionSerializer(data={
                'test': test.id,
                'subject': subjects[name].id,
                'question_text_uz': text,
                'question_type': 'choice',
                'score': item.get('score', 1),
                'order': order,
                'choices': [
                    {'letter': letter, 'text_uz': to_html(value), 'is_correct': letter == item['correct']}
                    for letter, value in item['choices'].items()
                ],
            })
            try:
                serializer.is_valid(raise_exception=True)
            except ValidationError as error:
                sys.exit(f'{number}-savolda xato, hech narsa saqlanmadi: {error.detail}')
            serializer.save()
            added += 1

    return test, added, len(data['questions']) - added


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    env = os.getenv('DJANGO_ENV', 'development')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'config.settings.{env}')

    import django
    django.setup()
    from django.conf import settings
    from django.db.models import Count

    data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
    print(f"Muhit: {env}, baza: {settings.DATABASES['default']['NAME']}")

    test, added, skipped = add_questions(data)
    print(test)
    for row in test.questions.values('subject__name').annotate(total=Count('id')).order_by('subject__name'):
        print(f"{row['subject__name']}: {row['total']} ta savol")
    print(f"Qo'shildi: {added}, oldin bor edi: {skipped}, testda jami: {test.questions.count()} / {test.question_count}")


if __name__ == '__main__':
    main()
