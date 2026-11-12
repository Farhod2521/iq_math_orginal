"""
Liga gollarini yangi qoida bo'yicha to'g'rilash: fanlardan gol = olingan tanga (1 tanga = 1 gol).

Mavsum ochilgan sanadan (LigaSeason.created_at) boshlab har bir ishtirokchi uchun:
  - tanga berilgan har bir misolga (StudentScoreLog.award_type='coin') 1 ta "Fanlarni ishlash" goli bo'lishi kerak
    — yo'q bo'lsa qo'shiladi;
  - tanga emas, ball berilgan misollar uchun yozilgan gollar (kunlik tanga chegarasidan keyingilar) o'chiriladi;
  - jami gol (LigaParticipant.points) barcha gol yozuvlari yig'indisidan qayta hisoblanadi.
Kunlik kirish va haftalik test gollari o'zgarmaydi.

Ishga tushirish (manage.py turgan papkada):
    python gol_sript.py              — barcha ochiq mavsumlarni to'g'rilaydi
    python gol_sript.py --dry        — faqat ko'rsatadi, bazaga yozmaydi
    python gol_sript.py --season 1   — faqat 1-mavsum (yopilgan bo'lsa ham)

Qayta ishga tushirish xavfsiz: ikkinchi marta hech narsa o'zgarmaydi.
"""
import argparse
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"config.settings.{os.getenv('DJANGO_ENV', 'development')}")
django.setup()

from django.db import transaction  # noqa: E402
from django.db.models import Sum  # noqa: E402

from django_app.app_liga.models import LigaParticipant, LigaPointLog, LigaSeason  # noqa: E402
from django_app.app_liga.services import SUBJECT_POINTS  # noqa: E402
from django_app.app_student.models import StudentScoreLog  # noqa: E402

SUBJECT = LigaPointLog.SOURCE_SUBJECT


class DryRun(Exception):
    pass


def fix_season(season):
    since = season.created_at
    participants = list(season.participants.select_related('student', 'grade').order_by('grade_id', '-points'))
    print(f"\n=== {season.number}-mavsum (ochilgan: {since:%d.%m.%Y %H:%M}), ishtirokchilar: {len(participants)} ===")
    if not participants:
        return 0, 0

    # Mavsum ochilgandan beri tanga berilgan misollar: student_id -> {score_log_id: awarded_at}
    coins = {}
    for log_id, student_id, awarded_at in StudentScoreLog.objects.filter(
        student_score__student_id__in=[p.student_id for p in participants],
        award_type='coin',
        awarded_at__gte=since,
    ).values_list('id', 'student_score__student_id', 'awarded_at'):
        coins.setdefault(student_id, {})[str(log_id)] = awarded_at

    header = f"{'Sinf':>4}  {'F.I.Sh.':<35} {'Tanga':>6} {'Fan goli':>15} {'Jami gol':>15}"
    print(header)
    print('-' * len(header))

    added_total = removed_total = 0
    for participant in participants:
        student_coins = coins.get(participant.student_id, {})
        subject_logs = {log.ref: log for log in participant.point_logs.filter(source=SUBJECT)}
        old_subject = sum(log.points for log in subject_logs.values())
        old_total = participant.points

        # Ball berilgan (tanga emas) misollar uchun yozilgan gollar
        extra = [log.id for ref, log in subject_logs.items() if ref not in student_coins]
        # Tanga olingan, lekin gol yozilmagan misollar
        missing = [ref for ref in student_coins if ref not in subject_logs]

        if extra:
            LigaPointLog.objects.filter(id__in=extra).delete()
        if missing:
            created = LigaPointLog.objects.bulk_create([
                LigaPointLog(participant=participant, source=SUBJECT, ref=ref, points=SUBJECT_POINTS)
                for ref in missing
            ])
            # Tarixda gol o'sha misol yechilgan vaqtda ko'rinsin
            for log in created:
                LigaPointLog.objects.filter(pk=log.pk).update(created_at=student_coins[log.ref])

        new_total = participant.point_logs.aggregate(total=Sum('points'))['total'] or 0
        if new_total != old_total:
            LigaParticipant.objects.filter(pk=participant.pk).update(points=new_total)
        new_subject = len(student_coins) * SUBJECT_POINTS

        added_total += len(missing)
        removed_total += len(extra)
        mark = '' if (old_subject, old_total) == (new_subject, new_total) else '  *'
        print(
            f"{participant.grade.name:>4}  {participant.student.full_name[:35]:<35} {len(student_coins):>6} "
            f"{f'{old_subject} -> {new_subject}':>15} {f'{old_total} -> {new_total}':>15}{mark}"
        )

    print(f"Qo'shildi: {added_total} gol yozuvi, o'chirildi: {removed_total} gol yozuvi")
    return added_total, removed_total


def main():
    parser = argparse.ArgumentParser(description="Liga fan gollarini tanga bo'yicha to'g'rilash")
    parser.add_argument('--dry', action='store_true', help="faqat ko'rsatish, bazaga yozmaslik")
    parser.add_argument('--season', type=int, help='mavsum raqami (bo\'lmasa — barcha ochiq mavsumlar)')
    args = parser.parse_args()

    if args.season:
        seasons = LigaSeason.objects.filter(number=args.season)
    else:
        seasons = LigaSeason.objects.filter(closed_at__isnull=True)
    seasons = list(seasons.order_by('number'))
    if not seasons:
        print("Mavsum topilmadi")
        return

    try:
        with transaction.atomic():
            for season in seasons:
                fix_season(season)
            if args.dry:
                raise DryRun
    except DryRun:
        print("\n--dry: hech narsa saqlanmadi. Saqlash uchun: python gol_sript.py")
        return
    print("\nTayyor: o'zgarishlar saqlandi.")


if __name__ == '__main__':
    main()
