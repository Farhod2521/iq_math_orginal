"""Marketing bo'limi uchun statistika sahifasi: /market-statistika/

Kirish: .env dagi MARKET_STATS_CODE (4 xonali raqam). Kod sessiyada saqlanadi.
Brute-force himoyasi: bitta IP dan 5 ta xato urinish -> 15 daqiqa blok,
hamma IP lardan jami 30 ta xato -> sahifa 15 daqiqa yopiladi.
"""
import csv
import hmac
import os
import time
from collections import defaultdict
from datetime import date, datetime, time as dtime, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from django_app.app_battle.models import BattleParticipant
from django_app.app_book.models import BookPayment, BookPurchase
from django_app.app_liga.models import LigaParticipant
from django_app.app_payments.models import Payment, Subscription
from django_app.app_student.models import Diagnost_Student
from django_app.app_tutor.models import TutorCouponTransaction, TutorReferralTransaction
from django_app.app_user.models import Referral, Student, User

try:  # development sozlamasi .env ni o'qimaydi — shu yerda ham yuklab qo'yamiz
    from dotenv import load_dotenv
    load_dotenv(os.path.join(settings.BASE_DIR, '.env'))
except Exception:  # pragma: no cover
    pass


PAGE_URL = '/market-statistika/'
SESSION_KEY = 'market_stats_auth_at'
SESSION_TTL = 8 * 60 * 60          # 8 soat
MAX_ATTEMPTS_PER_IP = 5
MAX_ATTEMPTS_GLOBAL = 30
LOCK_SECONDS = 15 * 60
MAX_RANGE_DAYS = 731

ROLE_LABELS = {
    'student': "O'quvchi",
    'teacher': 'Mentor',
    'tutor': "Tutor (o'qituvchi)",
    'parent': 'Ota-ona',
}
USER_ROLES = list(ROLE_LABELS.keys())
PRESETS = [('1', 'Bugun'), ('7', '7 kun'), ('30', '30 kun'), ('90', '90 kun'), ('365', '1 yil')]
WEEKDAYS = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya']

ZERO = Value(Decimal('0'), output_field=DecimalField(max_digits=16, decimal_places=2))


# ───────────────────────── yordamchilar ─────────────────────────

def fmt_int(n):
    return f"{int(n or 0):,}".replace(',', ' ')


def fmt_money(n):
    return f"{fmt_int(round(float(n or 0)))} so'm"


def fmt_short_money(n):
    n = float(n or 0)
    if abs(n) >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f} mlrd".replace('.0 ', ' ')
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f} mln".replace('.0 ', ' ')
    if abs(n) >= 1_000:
        return f"{n / 1_000:.0f} ming"
    return fmt_int(n)


def pct(part, whole):
    return round(part * 100 / whole, 1) if whole else 0.0


def delta(cur, prev):
    """Oldingi davrga nisbatan o'zgarish (%). Oldingi 0 bo'lsa None."""
    cur, prev = float(cur or 0), float(prev or 0)
    if prev == 0:
        return None
    return round((cur - prev) * 100 / prev, 1)


def _num(v):
    return float(v or 0)


# ───────────────────────── kirish (auth) ─────────────────────────

def _configured_code():
    code = (os.getenv('MARKET_STATS_CODE') or '').strip()
    return code if len(code) == 4 and code.isdigit() else None


def _client_ip(request):
    return (request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR') or 'unknown').strip()


def _cache_get(key):
    try:
        return int(cache.get(key) or 0)
    except Exception:
        return 0


def _cache_incr(key):
    try:
        value = int(cache.get(key) or 0) + 1
        cache.set(key, value, LOCK_SECONDS)
        return value
    except Exception:
        return 0


def _cache_delete(key):
    try:
        cache.delete(key)
    except Exception:
        pass


def _is_authed(request):
    ts = request.session.get(SESSION_KEY)
    return bool(ts) and (time.time() - float(ts)) < SESSION_TTL


def _render_login(request, error=None, locked=False, status=200):
    return render(request, 'marketing/login.html', {
        'error': error,
        'locked': locked,
        'not_configured': _configured_code() is None,
    }, status=status)


def _handle_login(request):
    code = _configured_code()
    if code is None:
        return _render_login(request, status=503)

    ip_key = f'mkt_stats_fail_ip:{_client_ip(request)}'
    global_key = 'mkt_stats_fail_global'
    session_fails = int(request.session.get('mkt_stats_fails', 0))

    if (max(_cache_get(ip_key), session_fails) >= MAX_ATTEMPTS_PER_IP
            or _cache_get(global_key) >= MAX_ATTEMPTS_GLOBAL):
        return _render_login(request, locked=True, status=429)

    entered = ''.join(request.POST.get(f'd{i}', '') for i in range(4)) or request.POST.get('code', '')
    entered = entered.strip()

    if len(entered) == 4 and entered.isdigit() and hmac.compare_digest(entered, code):
        _cache_delete(ip_key)
        request.session.cycle_key()  # session fixation'dan himoya
        request.session[SESSION_KEY] = time.time()
        request.session.pop('mkt_stats_fails', None)
        return redirect(PAGE_URL)

    fails = max(_cache_incr(ip_key), session_fails + 1)
    _cache_incr(global_key)
    request.session['mkt_stats_fails'] = fails
    left = MAX_ATTEMPTS_PER_IP - fails
    if left <= 0:
        return _render_login(request, locked=True, status=429)
    return _render_login(request, error=f"Kod noto'g'ri. Yana {left} ta urinish qoldi.", status=401)


# ───────────────────────── davr (filter) ─────────────────────────

def _parse_range(request):
    today = timezone.localdate()
    preset = request.GET.get('p')
    start = end = None
    try:
        if request.GET.get('from') and request.GET.get('to'):
            start = date.fromisoformat(request.GET['from'])
            end = date.fromisoformat(request.GET['to'])
            preset = None
    except ValueError:
        start = end = None

    if start is None:
        preset = preset if preset in dict(PRESETS) else '30'
        days = int(preset)
        end = today
        start = today - timedelta(days=days - 1)

    if start > end:
        start, end = end, start
    end = min(end, today)
    start = max(start, end - timedelta(days=MAX_RANGE_DAYS - 1))
    return start, end, preset


def _aware(d):
    return timezone.make_aware(datetime.combine(d, dtime.min), timezone.get_current_timezone())


# ───────────────────────── statistika ─────────────────────────

def _paid_payments():
    return Payment.objects.filter(status='success').annotate(paid_at=Coalesce('payment_date', 'created_at'))


def _paid_books():
    return BookPayment.objects.filter(status='success').annotate(paid_at=Coalesce('payment_date', 'created_at'))


def _revenue(s, e):
    p = _paid_payments().filter(paid_at__gte=s, paid_at__lt=e).aggregate(
        sub=Coalesce(Sum('amount', filter=Q(purpose=Payment.PURPOSE_SUBSCRIPTION)), ZERO),
        liga=Coalesce(Sum('amount', filter=Q(purpose=Payment.PURPOSE_LIGA)), ZERO),
        cnt=Count('id'),
        payers=Count('student', distinct=True),
    )
    b = _paid_books().filter(paid_at__gte=s, paid_at__lt=e).aggregate(
        book=Coalesce(Sum('amount'), ZERO), cnt=Count('id'), payers=Count('user', distinct=True),
    )
    total = _num(p['sub']) + _num(p['liga']) + _num(b['book'])
    return {
        'sub': _num(p['sub']), 'liga': _num(p['liga']), 'book': _num(b['book']),
        'total': total, 'count': p['cnt'] + b['cnt'], 'payers': p['payers'],
    }


def _conversion(s, e):
    cohort = Student.objects.filter(user__date_joined__gte=s, user__date_joined__lt=e)
    total = cohort.count()
    paid = Payment.objects.filter(status='success', student__in=cohort).values('student').distinct().count()
    return total, paid


def build_stats(start, end):
    tz = timezone.get_current_timezone()
    now = timezone.now()
    s, e = _aware(start), _aware(end + timedelta(days=1))
    days = (end - start).days + 1
    ps, pe = s - timedelta(days=days), s

    users = User.objects.filter(role__in=USER_ROLES)

    # ── KPI ──
    new_users = users.filter(date_joined__gte=s, date_joined__lt=e).count()
    new_users_prev = users.filter(date_joined__gte=ps, date_joined__lt=pe).count()

    rev = _revenue(s, e)
    rev_prev = _revenue(ps, pe)

    arppu = rev['sub'] + rev['liga']
    arppu = arppu / rev['payers'] if rev['payers'] else 0
    arppu_prev = rev_prev['sub'] + rev_prev['liga']
    arppu_prev = arppu_prev / rev_prev['payers'] if rev_prev['payers'] else 0

    coh_total, coh_paid = _conversion(s, e)
    coh_total_prev, coh_paid_prev = _conversion(ps, pe)
    conv, conv_prev = pct(coh_paid, coh_total), pct(coh_paid_prev, coh_total_prev)

    def active_since(delta_):
        t = now - delta_
        return users.filter(Q(sessions__last_used__gte=t) | Q(last_login__gte=t)).distinct().count()

    active_1, active_7, active_30 = active_since(timedelta(days=1)), active_since(timedelta(days=7)), active_since(timedelta(days=30))

    subs = Subscription.objects.aggregate(
        paid=Count('id', filter=Q(is_paid=True, end_date__gte=now)),
        trial=Count('id', filter=Q(is_paid=False, end_date__gte=now)),
        expired=Count('id', filter=Q(end_date__lt=now)),
        expiring=Count('id', filter=Q(is_paid=True, end_date__gte=now, end_date__lt=now + timedelta(days=7))),
    )

    kpis = [
        {'key': 'new', 'label': "Yangi ro'yxatdan o'tganlar", 'value': fmt_int(new_users),
         'delta': delta(new_users, new_users_prev), 'hint': f"Oldingi davr: {fmt_int(new_users_prev)}"},
        {'key': 'revenue', 'label': 'Umumiy daromad', 'value': fmt_short_money(rev['total']) + " so'm",
         'delta': delta(rev['total'], rev_prev['total']), 'hint': fmt_money(rev['total'])},
        {'key': 'payments', 'label': "Muvaffaqiyatli to'lovlar", 'value': fmt_int(rev['count']),
         'delta': delta(rev['count'], rev_prev['count']), 'hint': f"{fmt_int(rev['payers'])} ta to'lovchi o'quvchi"},
        {'key': 'conv', 'label': "Ro'yxatdan → to'lov konversiyasi", 'value': f"{conv}%",
         'delta': round(conv - conv_prev, 1) if coh_total_prev else None, 'delta_unit': 'pp',
         'hint': f"{fmt_int(coh_paid)} / {fmt_int(coh_total)} yangi o'quvchi"},
        {'key': 'arppu', 'label': "O'rtacha to'lov (ARPPU)", 'value': fmt_short_money(arppu) + " so'm",
         'delta': delta(arppu, arppu_prev), 'hint': "Obuna + liga / to'lovchi"},
        {'key': 'active', 'label': 'Faol foydalanuvchilar (7 kun)', 'value': fmt_int(active_7),
         'delta': None, 'hint': f"24 soat: {fmt_int(active_1)} · 30 kun: {fmt_int(active_30)}"},
    ]

    # ── kunlik dinamika ──
    reg_by_day = dict(
        users.filter(date_joined__gte=s, date_joined__lt=e)
        .annotate(d=TruncDate('date_joined', tzinfo=tz)).values('d').annotate(c=Count('id')).values_list('d', 'c')
    )
    rev_by_day = defaultdict(float)
    for d, total in (_paid_payments().filter(paid_at__gte=s, paid_at__lt=e)
                     .annotate(d=TruncDate('paid_at', tzinfo=tz)).values('d').annotate(t=Sum('amount')).values_list('d', 't')):
        rev_by_day[d] += _num(total)
    for d, total in (_paid_books().filter(paid_at__gte=s, paid_at__lt=e)
                     .annotate(d=TruncDate('paid_at', tzinfo=tz)).values('d').annotate(t=Sum('amount')).values_list('d', 't')):
        rev_by_day[d] += _num(total)

    daily = []
    for i in range(days):
        d = start + timedelta(days=i)
        daily.append({'date': d.isoformat(), 'label': d.strftime('%d.%m'),
                      'reg': reg_by_day.get(d, 0), 'rev': round(rev_by_day.get(d, 0))})

    # ── voronka (shu davrda ro'yxatdan o'tgan o'quvchilar) ──
    cohort = Student.objects.filter(user__date_joined__gte=s, user__date_joined__lt=e)
    f_diag = Diagnost_Student.objects.filter(student__in=cohort).values('student').distinct().count()
    f_sub = Subscription.objects.filter(student__in=cohort).count()
    f_repeat = (Payment.objects.filter(status='success', student__in=cohort)
                .values('student').annotate(c=Count('id')).filter(c__gte=2).count())
    funnel = [
        {'label': "Ro'yxatdan o'tdi", 'value': coh_total},
        {'label': 'Diagnostika testini ishladi', 'value': f_diag},
        {'label': 'Tekin muddat / obuna ochildi', 'value': f_sub},
        {'label': "Birinchi to'lov", 'value': coh_paid},
        {'label': "Qayta to'lov (2+)", 'value': f_repeat},
    ]
    for step in funnel:
        step['pct'] = pct(step['value'], coh_total)
        step['fmt'] = fmt_int(step['value'])

    # ── foydalanuvchilar tarkibi ──
    role_rows = dict(users.values('role').annotate(c=Count('id')).values_list('role', 'c'))
    role_new = dict(users.filter(date_joined__gte=s, date_joined__lt=e)
                    .values('role').annotate(c=Count('id')).values_list('role', 'c'))
    total_users = sum(role_rows.values())
    roles = [{'label': ROLE_LABELS[r], 'value': role_rows.get(r, 0), 'fmt': fmt_int(role_rows.get(r, 0)),
              'pct': pct(role_rows.get(r, 0), total_users), 'new': fmt_int(role_new.get(r, 0))} for r in USER_ROLES]

    # ── qurilma ──
    dev_counts = defaultdict(int)
    for dev, c in users.filter(date_joined__gte=s, date_joined__lt=e).values('device').annotate(c=Count('id')).values_list('device', 'c'):
        key = (dev or '').strip().lower()
        label = {'web': 'Web', 'mobile': 'Mobile', 'android': 'Android', 'ios': 'iOS'}.get(key, key.capitalize() or "Noma'lum")
        dev_counts[label] += c
    dev_total = sum(dev_counts.values())
    devices = [{'label': k, 'value': v, 'fmt': fmt_int(v), 'pct': pct(v, dev_total)}
               for k, v in sorted(dev_counts.items(), key=lambda x: -x[1])]
    if len(devices) > 4:
        rest = sum(d['value'] for d in devices[3:])
        devices = devices[:3] + [{'label': 'Boshqa', 'value': rest, 'fmt': fmt_int(rest), 'pct': pct(rest, dev_total)}]

    # ── daromad manbalari ──
    sources = [
        {'label': 'Obuna (tariflar)', 'value': rev['sub']},
        {'label': 'Liga kirish to\'lovi', 'value': rev['liga']},
        {'label': 'Kitob sotuvi', 'value': rev['book']},
    ]
    for src in sources:
        src['fmt'] = fmt_money(src['value'])
        src['pct'] = pct(src['value'], rev['total'])

    tariffs = []
    for row in (_paid_payments().filter(paid_at__gte=s, paid_at__lt=e, purpose=Payment.PURPOSE_SUBSCRIPTION)
                .values('subscription_months').annotate(c=Count('id'), t=Sum('amount')).order_by('subscription_months')):
        tariffs.append({'label': f"{row['subscription_months']} oylik", 'count': row['c'],
                        'fmt_count': fmt_int(row['c']), 'value': _num(row['t']), 'fmt': fmt_money(row['t'])})
    tariff_total = sum(t['count'] for t in tariffs)
    for t in tariffs:
        t['pct'] = pct(t['count'], tariff_total)

    # ── to'lov holatlari (shu davrda yaratilgan) ──
    st = Payment.objects.filter(created_at__gte=s, created_at__lt=e).aggregate(
        ok=Count('id', filter=Q(status='success')), pending=Count('id', filter=Q(status='pending')),
        failed=Count('id', filter=Q(status='failed')),
        lost=Coalesce(Sum('amount', filter=Q(status__in=['pending', 'failed'])), ZERO),
    )
    st_total = st['ok'] + st['pending'] + st['failed']
    pay_status = {
        'ok': fmt_int(st['ok']), 'pending': fmt_int(st['pending']), 'failed': fmt_int(st['failed']),
        'ok_pct': pct(st['ok'], st_total), 'pending_pct': pct(st['pending'], st_total),
        'failed_pct': pct(st['failed'], st_total), 'lost': fmt_money(st['lost']), 'total': fmt_int(st_total),
    }

    # ── viloyatlar ──
    region_total = defaultdict(int)
    region_new = defaultdict(int)
    for reg, c in Student.objects.values('region').annotate(c=Count('id')).values_list('region', 'c'):
        region_total[(reg or '').strip() or "Ko'rsatilmagan"] += c
    for reg, c in cohort.values('region').annotate(c=Count('id')).values_list('region', 'c'):
        region_new[(reg or '').strip() or "Ko'rsatilmagan"] += c
    all_students = sum(region_total.values())
    regions_sorted = sorted(region_total.items(), key=lambda x: -x[1])
    regions = [{'label': k, 'value': v, 'fmt': fmt_int(v), 'pct': pct(v, all_students),
                'new': fmt_int(region_new.get(k, 0))} for k, v in regions_sorted[:14]]
    if len(regions_sorted) > 14:
        rest = sum(v for _, v in regions_sorted[14:])
        rest_new = sum(region_new.get(k, 0) for k, _ in regions_sorted[14:])
        regions.append({'label': 'Boshqalar', 'value': rest, 'fmt': fmt_int(rest), 'pct': pct(rest, all_students),
                        'new': fmt_int(rest_new)})
    region_max = max([r['value'] for r in regions] or [1]) or 1
    for r in regions:
        r['bar'] = round(r['value'] * 100 / region_max, 1)

    # ── kuponlar ──
    coupons = []
    for row in (_paid_payments().filter(paid_at__gte=s, paid_at__lt=e, coupon__isnull=False)
                .values('coupon__code', 'coupon_type')
                .annotate(c=Count('id'), disc=Coalesce(Sum('discount_percent'), 0), t=Sum('amount'),
                          orig=Coalesce(Sum('original_amount'), ZERO),
                          cb=Coalesce(Sum('student_cashback_amount'), ZERO), cbt=Coalesce(Sum('teacher_cashback_amount'), ZERO))
                .order_by('-t')[:10]):
        given = max(_num(row['orig']) - _num(row['t']), 0)
        coupons.append({
            'code': row['coupon__code'], 'type': {'tutor': 'Tutor', 'student': "O'quvchi", 'system': 'Tizim'}.get(row['coupon_type'] or '', '—'),
            'count': fmt_int(row['c']), 'disc': round(row['disc'] / row['c']) if row['c'] else 0,
            'revenue': fmt_money(row['t']), 'given': fmt_money(given),
            'cashback': fmt_money(_num(row['cb']) + _num(row['cbt'])),
        })

    # ── tutorlar (referal + kupon) ──
    tutors = defaultdict(lambda: {'name': '', 'students': set(), 'revenue': 0.0, 'bonus': 0.0, 'ref': 0, 'cpn': 0})
    for row in (TutorReferralTransaction.objects.filter(used_at__gte=s, used_at__lt=e)
                .values('tutor_id', 'tutor__full_name', 'student_id', 'payment_amount', 'bonus_amount')):
        t = tutors[row['tutor_id']]
        t['name'] = row['tutor__full_name']
        t['students'].add(row['student_id'])
        t['revenue'] += _num(row['payment_amount'])
        t['bonus'] += _num(row['bonus_amount'])
        t['ref'] += 1
    for row in (TutorCouponTransaction.objects.filter(used_at__gte=s, used_at__lt=e)
                .values('tutor_id', 'tutor__full_name', 'student_id', 'payment_amount', 'cashback_amount')):
        t = tutors[row['tutor_id']]
        t['name'] = row['tutor__full_name']
        t['students'].add(row['student_id'])
        t['revenue'] += _num(row['payment_amount'])
        t['bonus'] += _num(row['cashback_amount'])
        t['cpn'] += 1
    top_tutors = sorted(tutors.values(), key=lambda x: -x['revenue'])[:8]
    top_tutors = [{'name': t['name'] or '—', 'students': fmt_int(len(t['students'])), 'ref': fmt_int(t['ref']),
                   'cpn': fmt_int(t['cpn']), 'revenue': fmt_money(t['revenue']), 'bonus': fmt_money(t['bonus'])}
                  for t in top_tutors]

    # ── bo'limlar faolligi (noyob o'quvchilar) ──
    engagement = [
        {'label': 'Diagnostika', 'value': Diagnost_Student.objects.filter(create_date__gte=s, create_date__lt=e)
            .values('student').distinct().count()},
        {'label': 'Liga', 'value': LigaParticipant.objects.filter(joined_at__gte=s, joined_at__lt=e)
            .values('student').distinct().count()},
        {'label': 'Battle', 'value': BattleParticipant.objects.filter(student__isnull=False, room__created_at__gte=s,
                                                                      room__created_at__lt=e).values('student').distinct().count()},
        {'label': 'Kitob xaridi', 'value': BookPurchase.objects.filter(purchased_at__gte=s, purchased_at__lt=e)
            .values('user').distinct().count()},
        {'label': "Do'st taklif qildi", 'value': Referral.objects.filter(created_at__gte=s, created_at__lt=e)
            .values('referrer').distinct().count()},
    ]
    for item in engagement:
        item['fmt'] = fmt_int(item['value'])

    # ── ro'yxatdan o'tish vaqtlari (hafta kuni × soat) ──
    heat = [[0] * 24 for _ in range(7)]
    for dj in users.filter(date_joined__gte=s, date_joined__lt=e).values_list('date_joined', flat=True).iterator():
        local = timezone.localtime(dj, tz)
        heat[local.weekday()][local.hour] += 1
    heat_max = max(max(r) for r in heat) or 1

    # ── so'nggi to'lovlar ──
    recent = []
    for p in (Payment.objects.filter(created_at__gte=s, created_at__lt=e).select_related('student', 'plan')
              .order_by('-created_at')[:12]):
        recent.append({
            'name': p.student.full_name if p.student_id else '—',
            'what': 'Liga' if p.purpose == Payment.PURPOSE_LIGA else (p.plan.name if p.plan_id and p.plan.name else f"{p.subscription_months} oylik obuna"),
            'amount': fmt_money(p.amount), 'status': p.status,
            'gateway': (p.payment_gateway or 'multicard').capitalize(),
            'coupon': f"-{p.discount_percent}%" if p.discount_percent else '',
            'date': timezone.localtime(p.payment_date or p.created_at).strftime('%d.%m.%Y %H:%M'),
        })

    return {
        'range': {'start': start.isoformat(), 'end': end.isoformat(), 'days': days,
                  'label': f"{start.strftime('%d.%m.%Y')} – {end.strftime('%d.%m.%Y')}",
                  'prev_label': f"{(start - timedelta(days=days)).strftime('%d.%m.%Y')} – {(start - timedelta(days=1)).strftime('%d.%m.%Y')}"},
        'kpis': kpis,
        'daily': daily,
        'funnel': funnel,
        'roles': roles, 'total_users': fmt_int(total_users),
        'devices': devices, 'dev_total': fmt_int(dev_total),
        'sources': sources, 'rev_total': fmt_money(rev['total']),
        'tariffs': tariffs,
        'pay_status': pay_status,
        'subs': {k: fmt_int(v) for k, v in subs.items()},
        'regions': regions, 'all_students': fmt_int(all_students),
        'coupons': coupons,
        'tutors': top_tutors,
        'engagement': engagement,
        'heat': heat, 'heat_max': heat_max, 'weekdays': WEEKDAYS,
        'recent': recent,
        'generated_at': timezone.localtime(now).strftime('%d.%m.%Y %H:%M'),
    }


def _export_csv(data):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="marketing_{data["range"]["start"]}_{data["range"]["end"]}.csv"'
    response.write('﻿')  # Excel UTF-8 ni to'g'ri ochishi uchun
    w = csv.writer(response, delimiter=';')
    w.writerow(['Davr', data['range']['label']])
    w.writerow([])
    w.writerow(['Ko\'rsatkich', 'Qiymat', "O'zgarish %"])
    for k in data['kpis']:
        w.writerow([k['label'], k['value'], '' if k['delta'] is None else k['delta']])
    w.writerow([])
    w.writerow(['Sana', "Ro'yxatdan o'tganlar", "Daromad (so'm)"])
    for d in data['daily']:
        w.writerow([d['date'], d['reg'], d['rev']])
    w.writerow([])
    w.writerow(['Viloyat', "Jami o'quvchi", 'Shu davrda yangi'])
    for r in data['regions']:
        w.writerow([r['label'], r['value'], r['new']])
    return response


# ───────────────────────── view ─────────────────────────

@never_cache
@require_http_methods(['GET', 'POST'])
def market_stats_view(request):
    if request.method == 'POST':
        if request.POST.get('action') == 'logout':
            request.session.pop(SESSION_KEY, None)
            return redirect(PAGE_URL)
        return _handle_login(request)

    if _configured_code() is None or not _is_authed(request):
        request.session.pop(SESSION_KEY, None)
        return _render_login(request, status=503 if _configured_code() is None else 200)

    start, end, preset = _parse_range(request)
    data = build_stats(start, end)

    if request.GET.get('export') == 'csv':
        return _export_csv(data)

    return render(request, 'marketing/stats.html', {
        'data': data,
        'chart_data': {
            'daily': data['daily'], 'roles': data['roles'], 'devices': data['devices'],
            'sources': data['sources'], 'tariffs': data['tariffs'], 'engagement': data['engagement'],
            'heat': data['heat'], 'weekdays': data['weekdays'],
        },
        'presets': PRESETS,
        'preset': preset,
    })
