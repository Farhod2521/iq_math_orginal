"""
Sayt statistikasi:
  POST /api/v1/management/site-stats/track/  — frontend har sahifa ko'rishda yuboradi (hamma uchun ochiq)
  GET  /api/v1/management/site-stats/        — mentor/superadmin uchun yig'ma statistika

GET parametrlari:
  period = today | 7d | 30d | 90d | 365d   (default: today)
  date   = YYYY-MM-DD — davr shu kun bilan tugaydi (default: bugun)
"""
from datetime import datetime, time, timedelta

from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncDay, TruncHour, TruncMonth, TruncWeek
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django_app.app_management.models import SiteVisit
from django_app.app_management.permissions import IsTeacherOrSuperAdmin
from django_app.app_management.site_stats import (
    REGION_NAMES, detect_source, is_public_ip, normalize_region, resolve_ip, visitor_ip,
)
from django_app.app_payments.models import Payment, Subscription
from django_app.app_user.device_service import _parse_user_agent
from django_app.app_user.models import User

# Xodimlarning tashriflari statistikani buzmasligi uchun yozilmaydi
STAFF_ROLES = {"teacher", "admin", "superadmin"}
TRACK_RATE_LIMIT = 120  # bitta IP dan daqiqasiga

PERIOD_DAYS = {"today": 1, "7d": 7, "30d": 30, "90d": 90, "365d": 365}


def _optional_user(request):
    """Token bo'lsa foydalanuvchini aniqlaydi; yaroqsiz token tracking'ni to'xtatmaydi."""
    from django_app.app_user.authentication import DeviceJWTAuthentication
    try:
        result = DeviceJWTAuthentication().authenticate(request)
    except Exception:
        return None
    return result[0] if result else None


class SiteVisitTrackAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        ip = visitor_ip(request)
        rate_key = f"sitetrack-rate:{ip}"
        hits = cache.get_or_set(rate_key, 0, 60)
        if hits >= TRACK_RATE_LIMIT:
            return Response(status=status.HTTP_204_NO_CONTENT)
        try:
            cache.incr(rate_key)
        except ValueError:
            pass

        data = request.data
        visitor_id = str(data.get("visitor_id") or "").strip()[:64]
        session_id = str(data.get("session_id") or "").strip()[:64]
        path = str(data.get("path") or "").strip()[:300]
        if not visitor_id or not session_id or not path.startswith("/"):
            return Response({"detail": "visitor_id, session_id va path majburiy"}, status=status.HTTP_400_BAD_REQUEST)

        ua_string = request.META.get("HTTP_USER_AGENT", "")
        try:
            from user_agents import parse
            if parse(ua_string).is_bot:
                return Response(status=status.HTTP_204_NO_CONTENT)
        except ImportError:
            pass

        user = _optional_user(request)
        if user and user.role in STAFF_ROLES:
            return Response(status=status.HTTP_204_NO_CONTENT)

        is_entry = bool(data.get("is_entry"))
        referrer = str(data.get("referrer") or "")[:500]
        site_host = (request.headers.get("Origin") or "").split("//")[-1].split(":")[0].removeprefix("www.")
        _, device_type = _parse_user_agent(ua_string)

        visit = SiteVisit(
            visitor_id=visitor_id,
            session_id=session_id,
            user=user,
            path=path,
            referrer=referrer,
            source=detect_source(referrer, data.get("utm_source"), site_host),
            device_type=device_type,
            ip_address=ip,
            is_entry=is_entry,
        )
        if is_entry:
            visit.is_new_visitor = not SiteVisit.objects.filter(visitor_id=visitor_id).exists()

        # O'quvchining ro'yxatdagi viloyati IP dan aniqroq
        student = getattr(user, "student_profile", None) if user else None
        profile_region = normalize_region(student.region) if student else ""

        if not is_public_ip(ip):
            visit.geo_resolved = True
        else:
            geo = resolve_ip(ip)
            if geo is not None:
                visit.country_code = geo["country_code"]
                visit.country_name = geo["country_name"]
                visit.region = geo["region"]
                visit.geo_resolved = True

        # Cloudflare orqali kelsa davlat kodi sarlavhada tayyor bo'ladi
        cf_country = (request.META.get("HTTP_CF_IPCOUNTRY") or "").upper()
        if not visit.country_code and len(cf_country) == 2 and cf_country not in ("XX", "T1"):
            visit.country_code = cf_country

        if profile_region:
            visit.region = profile_region
            if not visit.country_code and visit.geo_resolved:
                visit.country_code, visit.country_name = "UZ", "Uzbekistan"

        visit.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _pct(part, total):
    return round(part * 100 / total, 1) if total else 0


def _distinct_visitors(qs):
    return qs.values("visitor_id").distinct().count()


class SiteStatisticsAPIView(APIView):
    permission_classes = [IsTeacherOrSuperAdmin]

    def get(self, request):
        period = request.query_params.get("period", "today")
        if period not in PERIOD_DAYS:
            period = "today"
        days = PERIOD_DAYS[period]

        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        try:
            end_date = datetime.strptime(request.query_params.get("date", ""), "%Y-%m-%d").date()
            end_date = min(end_date, today)
        except ValueError:
            end_date = today

        start_date = end_date - timedelta(days=days - 1)
        start = timezone.make_aware(datetime.combine(start_date, time.min), tz)
        end = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min), tz)
        prev_start = start - timedelta(days=days)

        visits = SiteVisit.objects.filter(created_at__gte=start, created_at__lt=end)
        prev_visits = SiteVisit.objects.filter(created_at__gte=prev_start, created_at__lt=start)

        return Response({
            "period": {
                "key": period,
                "start": start_date,
                "end": end_date,
                "granularity": "hour" if days == 1 else "month" if days > 90 else "day",
            },
            "cards": self._cards(visits, prev_visits, start, end, prev_start),
            "timeline": self._timeline(visits, start, end, days, tz),
            "regions": self._regions(visits),
            "countries": self._group(visits, "country_code", extra="country_name"),
            "devices": self._group(visits, "device_type", labels=dict(SiteVisit.DEVICE_CHOICES)),
            "sources": self._group(
                visits.filter(is_entry=True), "source",
                labels=dict(SiteVisit.SOURCE_CHOICES), distinct="session_id",
            ),
            "top_pages": self._top_pages(visits),
            "user_types": self._user_types(),
            "registrations": self._registrations(end_date, tz),
        })

    # ---------- bloklar ----------

    def _cards(self, visits, prev_visits, start, end, prev_start):
        def regs(a, b):
            return User.objects.filter(date_joined__gte=a, date_joined__lt=b).count()

        def subs(a, b):
            return (Payment.objects.filter(status="success", payment_date__gte=a, payment_date__lt=b)
                    .values("student").distinct().count())

        def active(qs):
            return qs.filter(user__isnull=False).values("user").distinct().count()

        def new_visitors(qs):
            return qs.filter(is_new_visitor=True).values("visitor_id").distinct().count()

        return {
            "visitors": {"value": _distinct_visitors(visits), "previous": _distinct_visitors(prev_visits)},
            "page_views": {"value": visits.count(), "previous": prev_visits.count()},
            "new_visitors": {"value": new_visitors(visits), "previous": new_visitors(prev_visits)},
            "registrations": {"value": regs(start, end), "previous": regs(prev_start, start)},
            "active_users": {"value": active(visits), "previous": active(prev_visits)},
            "new_subscriptions": {"value": subs(start, end), "previous": subs(prev_start, start)},
            "active_subscribers": {
                "value": Subscription.objects.filter(is_paid=True, end_date__gte=timezone.now()).count(),
            },
        }

    def _timeline(self, visits, start, end, days, tz):
        if days == 1:
            trunc, step = TruncHour, "hour"
        elif days > 90:
            trunc, step = TruncMonth, "month"
        else:
            trunc, step = TruncDay, "day"

        def series(qs, field, distinct=None):
            rows = qs.annotate(b=trunc(field, tzinfo=tz)).values("b")
            rows = rows.annotate(c=Count(distinct, distinct=True) if distinct else Count("id"))
            return {timezone.localtime(r["b"], tz).replace(tzinfo=None): r["c"] for r in rows if r["b"]}

        total = series(visits, "created_at", "visitor_id")
        new = series(visits.filter(is_new_visitor=True), "created_at", "visitor_id")
        regs = series(User.objects.filter(date_joined__gte=start, date_joined__lt=end), "date_joined")

        points = []
        cur = timezone.localtime(start, tz).replace(tzinfo=None)
        last = timezone.localtime(end, tz).replace(tzinfo=None)
        while cur < last:
            if step == "hour":
                label, nxt = cur.strftime("%H:00"), cur + timedelta(hours=1)
            elif step == "day":
                label, nxt = cur.strftime("%d.%m"), cur + timedelta(days=1)
            else:
                label = cur.strftime("%m.%Y")
                nxt = (cur.replace(day=1) + timedelta(days=32)).replace(day=1)
            key = cur.replace(day=1) if step == "month" else cur
            points.append({
                "label": label,
                "date": cur.isoformat(),
                "visitors": total.get(key, 0),
                "new_visitors": new.get(key, 0),
                "registrations": regs.get(key, 0),
            })
            cur = nxt
        return points

    def _regions(self, visits):
        uz = visits.filter(region__gt="")
        counts = dict(uz.values("region").annotate(c=Count("visitor_id", distinct=True)).values_list("region", "c"))
        total = sum(counts.values())
        items = [
            {"key": key, "name": name, "count": counts.get(key, 0), "percent": _pct(counts.get(key, 0), total)}
            for key, name in REGION_NAMES.items()
        ]
        items.sort(key=lambda x: -x["count"])
        return {"total": total, "items": items}

    def _group(self, qs, field, labels=None, extra=None, distinct="visitor_id"):
        values = [field, extra] if extra else [field]
        rows = list(qs.values(*values).annotate(c=Count(distinct, distinct=True)).order_by("-c"))
        if extra:  # bir xil kodga bir nechta nom tushmasligi uchun kod bo'yicha qo'shamiz
            merged = {}
            for r in rows:
                item = merged.setdefault(r[field], {field: r[field], extra: r[extra], "c": 0})
                item["c"] += r["c"]
                item[extra] = item[extra] or r[extra]
            rows = sorted(merged.values(), key=lambda r: -r["c"])
        total = sum(r["c"] for r in rows)
        items = []
        for r in rows:
            item = {"key": r[field] or "unknown", "count": r["c"], "percent": _pct(r["c"], total)}
            if labels:
                item["label"] = labels.get(r[field], r[field])
            if extra:
                item["name"] = r[extra] or ""
            items.append(item)
        return {"total": total, "items": items}

    def _top_pages(self, visits, limit=10):
        total = visits.count()
        rows = visits.values("path").annotate(views=Count("id"), visitors=Count("visitor_id", distinct=True))
        return [
            {"path": r["path"], "views": r["views"], "visitors": r["visitors"], "percent": _pct(r["views"], total)}
            for r in rows.order_by("-views")[:limit]
        ]

    def _user_types(self):
        counts = dict(User.objects.values("role").annotate(c=Count("id")).values_list("role", "c"))
        main = ["student", "tutor", "parent", "teacher"]
        items = [{"key": role, "count": counts.get(role, 0)} for role in main]
        items.append({"key": "other", "count": sum(c for r, c in counts.items() if r not in main)})
        total = sum(i["count"] for i in items)
        for i in items:
            i["percent"] = _pct(i["count"], total)
        return {"total": total, "items": items}

    def _registrations(self, end_date, tz):
        """Yangi foydalanuvchilar: oxirgi 7 kun / 8 hafta / 12 oy."""
        end = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min), tz)

        def build(trunc, buckets):
            first = buckets[0]
            start = timezone.make_aware(datetime.combine(first, time.min), tz)
            rows = (User.objects.filter(date_joined__gte=start, date_joined__lt=end)
                    .annotate(b=trunc("date_joined", tzinfo=tz)).values("b").annotate(c=Count("id")))
            counts = {timezone.localtime(r["b"], tz).date(): r["c"] for r in rows if r["b"]}
            return [{"date": b, "count": counts.get(b, 0)} for b in buckets]

        days = [end_date - timedelta(days=i) for i in range(6, -1, -1)]
        week0 = end_date - timedelta(days=end_date.weekday())
        weeks = [week0 - timedelta(weeks=i) for i in range(7, -1, -1)]
        month0 = end_date.replace(day=1)
        months = []
        m = month0
        for _ in range(12):
            months.insert(0, m)
            m = (m - timedelta(days=1)).replace(day=1)

        return {
            "day": build(TruncDay, days),
            "week": build(TruncWeek, weeks),
            "month": build(TruncMonth, months),
        }


PROFILE_RELATIONS = ("student_profile", "tutor_profile", "parent_profile", "teacher_profile")


class SiteRegistrationsListAPIView(APIView):
    """
    Grafikdagi ustun bosilganda: shu davrda ro'yxatdan o'tgan foydalanuvchilar.
    GET /api/v1/management/site-stats/registrations/?start=2026-10-06&end=2026-10-12&page=1&page_size=20
      start, end — YYYY-MM-DD (ikkalasi ham kiradi); role, search — ixtiyoriy
    """
    permission_classes = [IsTeacherOrSuperAdmin]

    def get(self, request):
        tz = timezone.get_current_timezone()
        try:
            start_date = datetime.strptime(request.query_params.get("start", ""), "%Y-%m-%d").date()
            end_date = datetime.strptime(
                request.query_params.get("end") or request.query_params.get("start", ""), "%Y-%m-%d"
            ).date()
        except ValueError:
            return Response({"detail": "start va end YYYY-MM-DD formatida bo'lishi kerak"}, status=status.HTTP_400_BAD_REQUEST)

        start = timezone.make_aware(datetime.combine(start_date, time.min), tz)
        end = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min), tz)

        users = (User.objects.filter(date_joined__gte=start, date_joined__lt=end)
                 .select_related(*PROFILE_RELATIONS, "student_profile__subscription")
                 .order_by("-date_joined"))

        role = request.query_params.get("role")
        if role:
            users = users.filter(role=role)
        search = (request.query_params.get("search") or "").strip()
        if search:
            users = users.filter(
                Q(phone__icontains=search)
                | Q(student_profile__full_name__icontains=search)
                | Q(tutor_profile__full_name__icontains=search)
                | Q(parent_profile__full_name__icontains=search)
                | Q(teacher_profile__full_name__icontains=search)
            )

        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
        except ValueError:
            page, page_size = 1, 20

        count = users.count()
        offset = (page - 1) * page_size
        now = timezone.now()
        results = []
        for u in users[offset:offset + page_size]:
            profile = next((getattr(u, rel, None) for rel in PROFILE_RELATIONS if getattr(u, rel, None)), None)
            region = getattr(profile, "region", "") or ""
            sub = getattr(getattr(u, "student_profile", None), "subscription", None)
            subscription = None
            if sub:
                if sub.end_date and sub.end_date < now:
                    subscription = "expired"
                else:
                    subscription = "paid" if sub.is_paid else "trial"
            results.append({
                "id": u.id,
                "full_name": getattr(profile, "full_name", "") or "",
                "phone": u.phone,
                "role": u.role,
                "region": region,
                "region_key": normalize_region(region),
                "date_joined": timezone.localtime(u.date_joined, tz).isoformat(),
                "subscription": subscription,
            })

        return Response({"count": count, "page": page, "page_size": page_size, "results": results})
