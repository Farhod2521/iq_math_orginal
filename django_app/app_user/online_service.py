"""
Onlayn vaqtni hisoblash (UserOnlineSession).

touch_online  — token bilan kelgan har so'rovda chaqiriladi (ko'pi bilan daqiqada bir marta yozadi):
                oxirgi sessiya 5 daqiqa ichida faol bo'lsa — uzaytiradi, aks holda yangisini ochadi.
close_online  — chiqish (logout) paytida joriy sessiyani yopadi.
online_stats  — ota-ona / o'qituvchi sahifasi uchun: kirish-chiqishlar, hafta/oy/yil bo'yicha
                onlayn vaqt, o'rtacha, eng kam va eng ko'p kunlar, sessiyalar, soatlar kesimi.
"""
from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.utils import timezone

TZ = ZoneInfo("Asia/Tashkent")
SESSION_GAP = timedelta(minutes=5)  # shundan uzoq jimlikdan keyin yangi sessiya
TOUCH_EVERY = 60  # soniya: bazaga ko'pi bilan daqiqada bir yoziladi
TAIL = timedelta(seconds=TOUCH_EVERY)  # oxirgi belgidan keyingi faol vaqt (ping oralig'i)
_TOUCH_CACHE = "uonline:{}"


def touch_online(user_id):
    """Foydalanuvchini hozir onlayn deb belgilaydi. Xato bo'lsa so'rovni to'xtatmaydi."""
    if not user_id:
        return
    key = _TOUCH_CACHE.format(user_id)
    try:
        if cache.get(key):
            return
        cache.set(key, True, TOUCH_EVERY)
        from .models import UserOnlineSession

        now = timezone.now()
        session = UserOnlineSession.objects.filter(
            user_id=user_id, ended_at__isnull=True, last_seen_at__gte=now - SESSION_GAP,
        ).order_by("-last_seen_at").first()
        if session:
            UserOnlineSession.objects.filter(pk=session.pk).update(last_seen_at=now)
        else:
            UserOnlineSession.objects.create(user_id=user_id, started_at=now, last_seen_at=now)
    except Exception:
        pass


def close_online(user_id):
    """Chiqishda joriy sessiyani yopadi."""
    if not user_id:
        return
    try:
        from .models import UserOnlineSession

        now = timezone.now()
        UserOnlineSession.objects.filter(
            user_id=user_id, ended_at__isnull=True, last_seen_at__gte=now - SESSION_GAP,
        ).update(ended_at=now, last_seen_at=now)
        cache.delete(_TOUCH_CACHE.format(user_id))
    except Exception:
        pass


def _session_end(session, now):
    """Sessiya tugagan vaqt: chiqish yoki oxirgi faollik + ping oralig'i (hozirgi vaqtdan oshmaydi)."""
    if session.ended_at:
        return session.ended_at
    return min(session.last_seen_at + TAIL, now)


def _is_active(session, now):
    return session.ended_at is None and session.last_seen_at >= now - SESSION_GAP


def _overlap(start, end, a, b):
    return max(0.0, (min(end, b) - max(start, a)).total_seconds())


def _split_by_day_and_hour(start, end, by_day, by_hour):
    """Sessiyani Toshkent vaqti bo'yicha kunlar va soatlarga taqsimlaydi."""
    cur = start.astimezone(TZ)
    end = end.astimezone(TZ)
    while cur < end:
        next_hour = (cur.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
        piece_end = min(next_hour, end)
        seconds = (piece_end - cur).total_seconds()
        by_day[cur.date()] += seconds
        by_hour[cur.hour] += seconds
        cur = piece_end


def online_stats(user, recent_limit=10):
    from .models import UserOnlineSession

    now = timezone.now()
    today = now.astimezone(TZ).date()
    day_start = datetime.combine(today, time.min, tzinfo=TZ)
    windows = {
        "today": day_start,
        "week": day_start - timedelta(days=6),
        "month": day_start - timedelta(days=29),
        "year": day_start - timedelta(days=364),
    }

    sessions = list(
        UserOnlineSession.objects.filter(user=user, last_seen_at__gte=windows["year"]).order_by("started_at")
    )

    totals = {key: 0.0 for key in windows}
    by_day = defaultdict(float)  # oxirgi 30 kun
    by_hour = defaultdict(float)  # oxirgi 30 kun, soat bo'yicha
    month_sessions = []
    for s in sessions:
        end = _session_end(s, now)
        for key, start in windows.items():
            totals[key] += _overlap(s.started_at, end, start, now)
        if end > windows["month"]:
            _split_by_day_and_hour(max(s.started_at, windows["month"]), end, by_day, by_hour)
            month_sessions.append((s, (end - s.started_at).total_seconds()))

    active_days = {day: sec for day, sec in by_day.items() if sec >= 60}
    durations = [sec for _, sec in month_sessions if sec >= 60]

    def day_item(day):
        return {"date": day.isoformat(), "seconds": int(active_days[day])} if day else None

    max_day = max(active_days, key=active_days.get) if active_days else None
    min_day = min(active_days, key=active_days.get) if active_days else None
    longest = max(month_sessions, key=lambda x: x[1]) if month_sessions else None
    peak_hour = max(by_hour, key=by_hour.get) if by_hour else None

    recent = []
    for s in sorted(sessions, key=lambda x: x.started_at, reverse=True)[:recent_limit]:
        end = _session_end(s, now)
        active = _is_active(s, now)
        recent.append({
            "started_at": s.started_at.isoformat(),
            "ended_at": None if active else end.isoformat(),
            "seconds": int((end - s.started_at).total_seconds()),
            "active": active,
        })

    first = UserOnlineSession.objects.filter(user=user).order_by("started_at").values_list("started_at", flat=True).first()

    return {
        "online_now": bool(sessions) and _is_active(sessions[-1], now),
        "tracking_since": first.isoformat() if first else None,
        "totals": {key: int(value) for key, value in totals.items()},
        "average": {
            # Faol kunlardagi o'rtacha (oxirgi 30 kun)
            "per_day": int(sum(active_days.values()) / len(active_days)) if active_days else 0,
            "per_session": int(sum(durations) / len(durations)) if durations else 0,
        },
        "active_days": len(active_days),
        "max_day": day_item(max_day),
        "min_day": day_item(min_day),
        "longest_session": {"started_at": longest[0].started_at.isoformat(), "seconds": int(longest[1])} if longest else None,
        "peak_hour": peak_hour,
        "daily": [
            {"date": (today - timedelta(days=o)).isoformat(), "seconds": int(by_day.get(today - timedelta(days=o), 0))}
            for o in range(6, -1, -1)
        ],
        "by_hour": [int(by_hour.get(h, 0)) for h in range(24)],
        "sessions": recent,
    }
