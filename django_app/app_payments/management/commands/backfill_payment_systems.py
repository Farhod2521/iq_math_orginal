"""Eski to'lovlarning haqiqiy to'lov tizimini (click, payme, uzum, uzcard, humo...) Multicard'dan olib to'ldirish.

2026-10-06 gacha callback'dagi `ps` saqlanmagan — u to'lovlarda payment_gateway="multicard"
bo'lib qolgan. Bu buyruq har bir shunday to'lov uchun Multicard'dan tranzaksiya ma'lumotini
(`GET /payment/{uuid}`) so'raydi va `ps` (hamda bo'lsa `card_pan`) ni yozadi.

Ishlatish:
    python manage.py backfill_payment_systems            # faqat ko'rsatadi (bazaga yozmaydi)
    python manage.py backfill_payment_systems --limit 5  # avval 5 tasini sinab ko'rish
    python manage.py backfill_payment_systems --apply    # bazaga yozish
"""
import json
import time

import requests
from django.core.management.base import BaseCommand
from django.db.models import Q

from django_app.app_payments.models import Payment
from django_app.app_payments.utils import MULTICARD_BASE_URL, get_multicard_token, normalize_payment_system


def _find(data, *keys):
    """Javob ichidan kalitni qidirish: {"data": {...}} yoki {"data": {"payment": {...}}} ko'rinishlari uchun."""
    stack = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for k in keys:
                if node.get(k):
                    return node[k]
            stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
        elif isinstance(node, list):
            stack.extend(node)
    return None


class Command(BaseCommand):
    help = "Eski to'lovlardagi 'multicard' o'rniga haqiqiy to'lov tizimini Multicard API'dan olib yozadi."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Bazaga yozish (aks holda faqat ko'rsatadi).")
        parser.add_argument("--limit", type=int, default=0, help="Nechta to'lovni tekshirish (0 = hammasi).")
        parser.add_argument("--sleep", type=float, default=0.2, help="So'rovlar orasidagi pauza (soniya).")
        parser.add_argument("--verbose-json", action="store_true", help="Multicard javobini to'liq chiqarish.")

    def handle(self, *args, **opts):
        qs = (
            Payment.objects.filter(status="success")
            .filter(Q(payment_gateway__isnull=True) | Q(payment_gateway="") | Q(payment_gateway__iexact="multicard"))
            .exclude(Q(uuid__isnull=True) | Q(uuid=""))
            .order_by("-created_at")
        )
        if opts["limit"]:
            qs = qs[: opts["limit"]]
        payments = list(qs)

        missing_uuid = (
            Payment.objects.filter(status="success")
            .filter(Q(payment_gateway__isnull=True) | Q(payment_gateway="") | Q(payment_gateway__iexact="multicard"))
            .filter(Q(uuid__isnull=True) | Q(uuid=""))
            .count()
        )

        self.stdout.write(f"Tekshiriladigan to'lovlar: {len(payments)} (uuid'siz, tiklab bo'lmaydiganlar: {missing_uuid})")
        if not payments:
            return

        token = get_multicard_token()
        headers = {"Authorization": f"Bearer {token}"}
        updated = not_found = failed = 0

        for p in payments:
            url = f"{MULTICARD_BASE_URL}/payment/{p.uuid}"
            try:
                r = requests.get(url, headers=headers, timeout=15)
                if r.status_code == 401:  # token eskirgan bo'lsa — yangilab, qayta urinish
                    token = get_multicard_token()
                    headers = {"Authorization": f"Bearer {token}"}
                    r = requests.get(url, headers=headers, timeout=15)
                body = r.json() if r.content else {}
            except Exception as e:  # noqa: BLE001
                failed += 1
                self.stderr.write(f"#{p.id}: so'rov xatosi — {e}")
                continue

            if opts["verbose_json"]:
                self.stdout.write(f"#{p.id} [{r.status_code}] {json.dumps(body, ensure_ascii=False)[:1500]}")

            ps = normalize_payment_system(_find(body, "ps", "payment_system"))
            card_pan = _find(body, "card_pan")

            if r.status_code != 200 or not ps:
                not_found += 1
                self.stdout.write(f"#{p.id}: tizim topilmadi (HTTP {r.status_code})")
                continue

            self.stdout.write(f"#{p.id} {p.student.full_name if p.student_id else '—'}: multicard -> {ps}")
            if opts["apply"]:
                fields = ["payment_gateway"]
                p.payment_gateway = ps
                if card_pan and not p.card_pan:
                    p.card_pan = str(card_pan)[:32]
                    fields.append("card_pan")
                p.save(update_fields=fields)
            updated += 1
            time.sleep(opts["sleep"])

        mode = "YOZILDI" if opts["apply"] else "TOPILDI (yozilmadi, --apply bilan ishga tushiring)"
        self.stdout.write(self.style.SUCCESS(f"{mode}: {updated} | topilmadi: {not_found} | xato: {failed}"))
