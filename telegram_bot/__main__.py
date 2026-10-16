"""
Qo'lda ishga tushirish (loyiha ildizidan):

  python -m telegram_bot test        — admin va marketing chatlariga sinov xabari
  python -m telegram_bot marketing   — yangi o'quvchilarni hozir yuborish
  python -m telegram_bot backup      — backupni hozir yuborish (fayllar rejimi .telegram-env bo'yicha)
  python -m telegram_bot backup-full — backupni hozir yuborish (barcha fayllar bilan)
"""
import logging
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"config.settings.{os.getenv('DJANGO_ENV', 'production')}")
    import django

    django.setup()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    from . import config
    from .backup import run_backup
    from .marketing import notify_new_students
    from .telegram_api import broadcast

    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command == "test":
        print("admin:", broadcast(config.ADMIN_CHAT_IDS, "✅ IQMATH bot: admin chat ulandi"))
        print("marketing:", broadcast(config.MARKETING_CHAT_IDS, "✅ IQMATH bot: marketing chat ulandi"))
    elif command == "marketing":
        print("yuborildi:", notify_new_students())
    elif command in ("backup", "backup-full"):
        print("muvaffaqiyatli:", run_backup(force_full=command == "backup-full"))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
