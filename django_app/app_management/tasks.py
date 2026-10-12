import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import SiteVisit
from .site_stats import is_public_ip, lookup_ips


logger = logging.getLogger(__name__)

GEO_BATCH_SIZE = 100  # ip-api batch chegarasi


@shared_task(name="django_app.app_management.tasks.resolve_site_visit_geo_task")
def resolve_site_visit_geo_task():
    """
    Davlati aniqlanmagan tashriflar uchun IP bo'yicha davlat va viloyatni topadi.
    Har daqiqada ko'pi bilan GEO_BATCH_SIZE ta yangi IP tekshiriladi.
    """
    pending = SiteVisit.objects.filter(
        geo_resolved=False, created_at__gte=timezone.now() - timedelta(days=3)
    )
    ips = list(pending.values_list("ip_address", flat=True).distinct()[:GEO_BATCH_SIZE])
    if not ips:
        return {"resolved_ips": 0}

    lookup = [ip for ip in ips if is_public_ip(ip)]
    geo_by_ip = lookup_ips(lookup) if lookup else {}

    for ip in ips:
        geo = geo_by_ip.get(ip)
        if geo is None and ip in lookup:
            continue  # servis javob bermadi — keyingi safar qayta urinamiz
        rows = pending.filter(ip_address=ip)
        if geo:
            rows.update(country_code=geo["country_code"], country_name=geo["country_name"])
            # O'quvchi profilidan olingan viloyat ustidan yozmaymiz
            if geo["region"]:
                rows.filter(region="").update(region=geo["region"])
        rows.update(geo_resolved=True)

    logger.info("Site visit geo resolved for %s IPs", len(geo_by_ip))
    return {"resolved_ips": len(geo_by_ip)}
