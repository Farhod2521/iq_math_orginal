"""
Mahsulot ko'rsatkichlari (faqat o'quvchilar) — sayt statistikasi sahifasidagi bloklar:

  student_status — o'quvchilar obuna holati bo'yicha: sinov muddatida, bepul, 1/3/... oylik, muddati tugagan
  conversion     — kumulyativ konversiya (kamida bir marta to'laganlar / barcha o'quvchilar)
                   va 30 kunlik moving average (30 kunda birinchi marta to'laganlar / 30 kunda ro'yxatdan o'tganlar)
  retention      — D30: oxirgi 30 kunda faol bo'lganlar ulushi, jami va yangi o'quvchilar uchun alohida
                   (faollik UserDailyActivity dan — sayt va mobil ilova so'rovlari)
"""
from datetime import datetime, time, timedelta

from django.core.cache import cache
from django.db.models import Count, Exists, Min, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from django_app.app_payments.models import Payment
from django_app.app_user.models import Student, UserDailyActivity

WINDOW = 30  # moving average va D30 oynasi (kun)
CACHE_TTL = 300


def _pct(part, total):
    return round(part * 100 / total, 1) if total else 0


def _aware(d, tz):
    return timezone.make_aware(datetime.combine(d, time.min), tz)


def build_product_metrics(end_date, days, tz):
    """end_date — davr oxiri; days — tanlangan davr uzunligi (grafik shuncha kunni ko'rsatadi, kamida 30)."""
    series_days = min(max(days, WINDOW), 365)
    key = f"site_stats:product:{end_date.isoformat()}:{series_days}"
    return cache.get_or_set(
        key, lambda: {
            "student_status": _student_status(),
            "conversion": _conversion(end_date, series_days, tz),
            "retention": _retention(end_date, tz),
        }, CACHE_TTL,
    )


# ---------- o'quvchilar statusi ----------

def _student_status():
    now = timezone.now()
    success = Payment.objects.filter(student=OuterRef("pk"), status="success")
    last_months = success.order_by("-payment_date", "-created_at").values("subscription_months")[:1]

    students = Student.objects.annotate(ever_paid=Exists(success), months=Subquery(last_months))
    active_paid = Q(subscription__is_paid=True, subscription__end_date__gte=now)

    total = students.count()
    paid_rows = (students.filter(active_paid).values("months")
                 .annotate(c=Count("id")).order_by("months"))
    trial = students.filter(
        subscription__is_paid=False, subscription__end_date__gte=now, ever_paid=False,
    ).count()
    expired = students.filter(ever_paid=True).exclude(active_paid).count()

    items = [{"key": "trial", "count": trial}]
    paid_total = 0
    for row in paid_rows:
        months = row["months"]
        paid_total += row["c"]
        # To'lovsiz (admin tomonidan berilgan) obunalar "other" ga tushadi
        items.append({"key": f"paid_{months}" if months else "paid_other", "months": months, "count": row["c"]})
    items.append({"key": "expired", "count": expired})
    # Qolganlari: sinov muddati tugagan va hech qachon to'lamagan (yoki obunasi umuman yo'q)
    free = max(total - trial - paid_total - expired, 0)
    items.insert(1, {"key": "free", "count": free})

    for i in items:
        i["percent"] = _pct(i["count"], total)
    return {"total": total, "paid": paid_total, "paid_percent": _pct(paid_total, total), "items": items}


# ---------- konversiya ----------

def _conversion(end_date, series_days, tz):
    series_start = end_date - timedelta(days=series_days - 1)
    base_start = series_start - timedelta(days=WINDOW - 1)  # birinchi nuqtaning 30 kunlik oynasi
    base_dt, end_dt = _aware(base_start, tz), _aware(end_date + timedelta(days=1), tz)

    # Ro'yxatdan o'tishlar (kun bo'yicha)
    regs = Student.objects.filter(user__date_joined__lt=end_dt)
    regs_before = regs.filter(user__date_joined__lt=base_dt).count()
    reg_by_day = dict(
        regs.filter(user__date_joined__gte=base_dt)
        .annotate(d=TruncDate("user__date_joined", tzinfo=tz)).values("d")
        .annotate(c=Count("id")).values_list("d", "c")
    )

    # Birinchi muvaffaqiyatli to'lov sanasi (o'quvchi bo'yicha)
    first_pay = (Payment.objects.filter(status="success")
                 .values("student")
                 .annotate(first=Min(Coalesce("payment_date", "created_at"))))
    pays_before = 0
    pay_by_day = {}
    for row in first_pay.filter(first__lt=end_dt):
        if row["first"] < base_dt:
            pays_before += 1
        else:
            d = timezone.localtime(row["first"], tz).date()
            pay_by_day[d] = pay_by_day.get(d, 0) + 1

    # Kunma-kun yig'amiz: kumulyativ va 30 kunlik oynadagi qiymatlar
    all_days = [base_start + timedelta(days=i) for i in range((end_date - base_start).days + 1)]
    cum_regs, cum_pays = regs_before, pays_before
    win_regs, win_pays = [], []
    series = []
    for d in all_days:
        r, p = reg_by_day.get(d, 0), pay_by_day.get(d, 0)
        cum_regs += r
        cum_pays += p
        win_regs.append(r)
        win_pays.append(p)
        if len(win_regs) > WINDOW:
            win_regs.pop(0)
            win_pays.pop(0)
        if d >= series_start:
            series.append({
                "date": d,
                "cumulative": _pct(cum_pays, cum_regs),
                "ma30": _pct(sum(win_pays), sum(win_regs)),
                "registrations_30d": sum(win_regs),
                "paid_30d": sum(win_pays),
            })

    last = series[-1] if series else {"cumulative": 0, "ma30": 0, "registrations_30d": 0, "paid_30d": 0}
    # 30 kun oldingi qiymat bilan solishtirish uchun
    prev = series[-1 - WINDOW] if len(series) > WINDOW else None
    return {
        "cumulative": {"value": last["cumulative"], "paid": cum_pays, "students": cum_regs},
        "ma30": {
            "value": last["ma30"],
            "previous": prev["ma30"] if prev else None,
            "paid": last["paid_30d"],
            "registrations": last["registrations_30d"],
        },
        "series": series,
    }


# ---------- D30 retention ----------

def _active_students(start_date, end_date):
    return (UserDailyActivity.objects
            .filter(user__role="student", date__gte=start_date, date__lte=end_date))


def _retention_point(end_date, tz):
    window_start = end_date - timedelta(days=WINDOW - 1)
    end_dt = _aware(end_date + timedelta(days=1), tz)
    window_dt = _aware(window_start, tz)

    # Jami: oxirgi 30 kunda kamida bir kun faol bo'lganlar / shu kungacha ro'yxatdan o'tgan barcha o'quvchilar
    students = Student.objects.filter(user__date_joined__lt=end_dt).count()
    active = _active_students(window_start, end_date).values("user").distinct().count()

    # Yangi: oxirgi 30 kunda ro'yxatdan o'tganlar; faol = ro'yxatdan o'tgan kunidan keyin yana qaytib kelgan
    new_users = Student.objects.filter(user__date_joined__gte=window_dt, user__date_joined__lt=end_dt)
    new_count = new_users.count()
    new_ids = set(new_users.values_list("user_id", flat=True))
    joined = dict(new_users.annotate(j=TruncDate("user__date_joined", tzinfo=tz)).values_list("user_id", "j"))
    returned = set()
    if new_ids:
        for uid, d in (UserDailyActivity.objects
                       .filter(user_id__in=new_ids, date__gte=window_start, date__lte=end_date)
                       .values_list("user_id", "date")):
            if d > joined.get(uid, d):
                returned.add(uid)

    return {
        "date": end_date,
        "total": {"value": _pct(active, students), "active": active, "students": students},
        "new": {"value": _pct(len(returned), new_count), "active": len(returned), "students": new_count},
    }


def _retention(end_date, tz):
    current = _retention_point(end_date, tz)
    # Oxirgi 12 hafta — haftalik nuqtalar (har biri o'zining 30 kunlik oynasi bilan)
    series = [current if i == 0 else _retention_point(end_date - timedelta(weeks=i), tz)
              for i in range(11, -1, -1)]
    first = UserDailyActivity.objects.aggregate(d=Min("date"))["d"]
    return {
        **current,
        "series": series,
        # Faollik shu sanadan beri yig'ilmoqda — undan oldingi nuqtalar to'liq emas
        "data_since": first,
    }
