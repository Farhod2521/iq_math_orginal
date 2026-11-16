"""Audit bo'yicha admin paneldagi ma'lumotlarni tuzatish (FAQ, e'lonlar, tariflar).

Ishlatish:
    python manage.py fix_audit_content            # faqat ko'rsatadi, hech narsa o'zgarmaydi
    python manage.py fix_audit_content --apply    # o'zgarishlarni bazaga yozadi

Nima qiladi:
  N9  — FAQ: imlo xatolari, "tez orada" (do'kon allaqachon ishlaydi), eski telefon raqami,
        takror savol (#9 bilan bir xil bo'lgan "kimlar ro'yxatdan o'tishi mumkin")
  L8  — e'lon matnidagi "so'ngi" -> "so'nggi"
  K-3 — "Pro" tariflarga asosiy imkoniyatlar (darslar, mashqlar, statistika) belgilanadi
  O2  — tarif nomi o'zbekchada ham ruschadagidek (Progress / Premium) bo'ladi

Chegirma foizlari va narxlarga TEGMAYDI — bu biznes qarori.
Buyruq qayta ishga tushirilsa zarari yo'q (ikkinchi marta o'zgartiradigan narsa topmaydi).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from django_app.app_management.models import FAQ, Elon
from django_app.app_payments.models import SubscriptionBenefit, SubscriptionPlan

CALL_CENTER = '+998 78 888 18 81'

# (eski matn, yangi matn) — FAQ savol/javoblarining barcha til maydonlarida almashtiriladi
FAQ_REPLACEMENTS = [
    ('foydalanuchi', 'foydalanuvchi'),
    ('foydlanishi', 'foydalanishi'),
    ('+998 (78) 888 08 00', CALL_CENTER),
    ('+998 78 888 08 00', CALL_CENTER),
    (
        'Ushbu ballarni tez orada qimmatbaho sovg&#39;alarga almashtirishingiz mumkin bo&#39;ladi.',
        'Ushbu ballarni «Mahsulotlar» bo&#39;limida sovg&#39;alarga almashtirishingiz mumkin.',
    ),
    (
        "Ushbu ballarni tez orada qimmatbaho sovg'alarga almashtirishingiz mumkin bo'ladi.",
        "Ushbu ballarni «Mahsulotlar» bo'limida sovg'alarga almashtirishingiz mumkin.",
    ),
    (
        'Эти баллы в скором времени можно будет обменять на ценные подарки.',
        'Эти баллы можно обменять на подарки в разделе «Продукты».',
    ),
]

# Takror savol: "Platformadan kimlar foydalanishi mumkin?" savoli bilan bir xil mazmun
FAQ_DUPLICATE_QUESTION_UZ = "IQMATH platformasidan kimlar ro'yxatdan o'tishi mumkin?"
FAQ_KEEP_QUESTION_UZ_PREFIX = 'Platformadan kimlar foydalanishi mumkin'

ELON_REPLACEMENTS = [
    ('so&#39;ngi ', 'so&#39;nggi '),
    ("so'ngi ", "so'nggi "),
    ('so‘ngi ', 'so‘nggi '),
]

# Pro tariflar asosiy tarifdagi hamma narsani ham o'z ichiga oladi
BASE_BENEFIT_TITLES_UZ = ['Matematika darslari', 'Mashqlar va testlar', "O'zlashtirish statistikasi"]

FAQ_FIELDS = ['question_uz', 'question_ru', 'answer_uz', 'answer_ru']
ELON_FIELDS = ['title_uz', 'title_ru', 'text_uz', 'text_ru']


def replace_in_fields(obj, fields, replacements):
    """O'zgargan maydonlar ro'yxatini qaytaradi (obyektni saqlamaydi)."""
    changed = []
    for field in fields:
        value = getattr(obj, field, None)
        if not value:
            continue
        new_value = value
        for old, new in replacements:
            new_value = new_value.replace(old, new)
        if new_value != value:
            setattr(obj, field, new_value)
            changed.append(field)
    return changed


class Command(BaseCommand):
    help = "Audit bo'yicha FAQ, e'lon va tarif ma'lumotlarini tuzatadi (standart holatda faqat ko'rsatadi)"

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help="O'zgarishlarni bazaga yozish")

    def handle(self, *args, **options):
        apply_changes = options['apply']
        self.changes = 0

        with transaction.atomic():
            self.fix_faqs(apply_changes)
            self.fix_elons(apply_changes)
            self.fix_plans(apply_changes)
            if not apply_changes:
                transaction.set_rollback(True)

        if not self.changes:
            self.stdout.write(self.style.SUCCESS("O'zgartiradigan narsa yo'q — hammasi joyida."))
        elif apply_changes:
            self.stdout.write(self.style.SUCCESS(f"Tayyor: {self.changes} ta o'zgarish bazaga yozildi."))
        else:
            self.stdout.write(self.style.WARNING(
                f"{self.changes} ta o'zgarish topildi, bazaga YOZILMADI. Yozish uchun: --apply"
            ))

    def note(self, text):
        self.changes += 1
        self.stdout.write(f"  - {text}")

    def fix_faqs(self, apply_changes):
        self.stdout.write("FAQ:")
        for faq in FAQ.objects.all():
            changed = replace_in_fields(faq, FAQ_FIELDS, FAQ_REPLACEMENTS)
            if changed:
                self.note(f"#{faq.id} «{faq.question_uz}»: {', '.join(changed)} tuzatildi")
                if apply_changes:
                    faq.save(update_fields=changed)

        duplicate = FAQ.objects.filter(question_uz=FAQ_DUPLICATE_QUESTION_UZ).first()
        keeper_exists = FAQ.objects.filter(question_uz__startswith=FAQ_KEEP_QUESTION_UZ_PREFIX).exists()
        if duplicate and keeper_exists:
            self.note(f"#{duplicate.id} «{duplicate.question_uz}» o'chiriladi (takror savol)")
            if apply_changes:
                duplicate.delete()

    def fix_elons(self, apply_changes):
        self.stdout.write("E'lonlar:")
        for elon in Elon.objects.all():
            changed = replace_in_fields(elon, ELON_FIELDS, ELON_REPLACEMENTS)
            if changed:
                self.note(f"#{elon.id} «{elon.title_uz}»: {', '.join(changed)} tuzatildi")
                if apply_changes:
                    elon.save(update_fields=changed)

    def fix_plans(self, apply_changes):
        self.stdout.write("Tariflar:")
        base_benefits = list(SubscriptionBenefit.objects.filter(title_uz__in=BASE_BENEFIT_TITLES_UZ, is_active=True))

        for plan in SubscriptionPlan.objects.filter(is_active=True):
            name_uz = (plan.name_uz or '').strip()
            name_ru = (plan.name_ru or '').strip()

            # O2: bir xil tarif ikki tilda har xil nomlanmasin (Start / Progress / Premium)
            if name_ru and name_uz != name_ru:
                self.note(f"#{plan.id} ({plan.months} oy): nomi «{name_uz}» -> «{name_ru}»")
                if apply_changes:
                    plan.name_uz = name_ru
                    plan.save(update_fields=['name_uz'])

            # K-3: Pro tariflar asosiy imkoniyatlarsiz ko'rinmasin
            if 'pro' in f"{name_uz} {name_ru}".lower().split():
                current_ids = set(plan.benefits.values_list('id', flat=True))
                missing = [b for b in base_benefits if b.id not in current_ids]
                if missing:
                    titles = ', '.join(b.title_uz for b in missing)
                    self.note(f"#{plan.id} «{name_ru or name_uz}» ({plan.months} oy): qo'shiladi — {titles}")
                    if apply_changes:
                        plan.benefits.add(*missing)
