"""
Tariflarni qayta yaratish: eski tariflar va ularning imkoniyatlari o'chiriladi,
o'rniga "Start" va "Start Pro" (1, 3, 12 oylik) yoziladi.

Ishga tushirish (manage.py turgan papkada):
    python tarif.py

Narx mantig'i (tizimdagi qolgan kod bilan bir xil):
    price_per_month — butun muddatning chegirmasiz narxi (masalan 3 oylik: 3 × oylik narx)
    yakuniy narx    — price_per_month × (1 − discount_percent / 100)

To'lovlar tarifga havola bilan emas, oylar soni bilan saqlanadi —
eski tariflarni o'chirish to'lovlar tarixiga ta'sir qilmaydi.
"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"config.settings.{os.getenv('DJANGO_ENV', 'development')}")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.db import transaction  # noqa: E402

from django_app.app_payments.models import (  # noqa: E402
    SubscriptionBenefit,
    SubscriptionCategory,
    SubscriptionPlan,
)

# ---------- imkoniyatlar (ikki tilda) ----------
BENEFITS = {
    "lessons": ("Matematika darslari", "Уроки математики"),
    "practice": ("Mashqlar va testlar", "Упражнения и тесты"),
    "stats": ("O'zlashtirish statistikasi", "Статистика успеваемости"),
    "all_lessons": ("Barcha darsliklar", "Все учебные материалы"),
    "mentors": ("Mentorlar yordami", "Помощь менторов"),
    "parents": ("Ota-onalar nazorati", "Родительский контроль"),
    "advanced_stats": ("Kengaytirilgan statistika", "Расширенная статистика"),
}

# ---------- tariflar ----------
# (nom_uz, nom_ru, oylik asosiy narx, {oy: chegirma %}, imkoniyatlar, "Eng ommabop" belgisi)
TARIFFS = [
    (
        "Start", "Start", 300_000,
        {1: 84, 3: 85, 12: 90},
        ["lessons", "practice", "stats"],
        False,
    ),
    (
        "Start Pro", "Start Pro", 500_000,
        {1: 40, 3: 45, 12: 65},
        ["all_lessons", "mentors", "parents", "advanced_stats"],
        True,
    ),
]

POPULAR = {"slug": "popular", "title_uz": "Eng ommabop", "title_ru": "Самый популярный"}


def som(value):
    return f"{int(round(value)):,}".replace(",", " ") + " so'm"


@transaction.atomic
def main():
    old_plans = SubscriptionPlan.objects.count()
    old_benefits = SubscriptionBenefit.objects.count()
    SubscriptionPlan.objects.all().delete()
    SubscriptionBenefit.objects.all().delete()
    print(f"O'chirildi: {old_plans} ta tarif, {old_benefits} ta imkoniyat")

    benefits = {}
    for key, (title_uz, title_ru) in BENEFITS.items():
        benefits[key] = SubscriptionBenefit.objects.create(
            title=title_uz, title_uz=title_uz, title_ru=title_ru, is_active=True,
        )

    popular, _ = SubscriptionCategory.objects.update_or_create(
        slug=POPULAR["slug"],
        defaults={
            "title": POPULAR["title_uz"],
            "title_uz": POPULAR["title_uz"],
            "title_ru": POPULAR["title_ru"],
            "is_active": True,
        },
    )

    for name_uz, name_ru, monthly, discounts, benefit_keys, is_popular in TARIFFS:
        print(f"\n{name_uz}:")
        for months, discount in discounts.items():
            full = monthly * months
            plan = SubscriptionPlan.objects.create(
                name=name_uz,
                name_uz=name_uz,
                name_ru=name_ru,
                category=popular if is_popular else None,
                months=months,
                discount_percent=discount,
                price_per_month=full,
                is_active=True,
            )
            plan.benefits.set([benefits[key] for key in benefit_keys])
            final = full * (100 - discount) / 100
            print(f"  {months:>2} oylik: {som(full)} → -{discount}% → {som(final)}  (tejash: {som(full - final)})")

    print("\nTayyor.")


if __name__ == "__main__":
    main()
