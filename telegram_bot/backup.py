"""
Admin: kunlik backup — baza va saqlangan fayllar (kitoblar, rasmlar, ...).

Telegram bot 50 MB dan katta fayl qabul qilmaydi, shuning uchun har bir arxiv
BACKUP_PART_SIZE_MB (default 45 MB) lik bo'laklarga bo'linib yuboriladi.

Tiklash:
  Linux:   cat iqmath_db_2026-10-16.dump.part* > iqmath_db.dump
           pg_restore --clean --no-owner -d <baza_nomi> iqmath_db.dump
           cat iqmath_media_2026-10-16.tar.part* > media.tar && tar -xf media.tar
  Windows: copy /b iqmath_db_2026-10-16.dump.part001+iqmath_db_2026-10-16.dump.part002 iqmath_db.dump

Fayllar rejimi (BACKUP_MEDIA_MODE):
  incremental — har kuni faqat oxirgi muvaffaqiyatli backupdan keyin o'zgargan fayllar,
                yakshanba kuni (yoki birinchi marta) — hammasi
  full        — har kuni hammasi
"""
import hashlib
import html
import logging
import os
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import time
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from . import config, state
from .telegram_api import TelegramError, broadcast, resend_document, send_document

logger = logging.getLogger(__name__)

LOCK_FILE = config.BOT_DIR / "backup.lock"
LOCK_STALE_SECONDS = 12 * 60 * 60


def _human(size):
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.2f} GB"


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Baza
# ---------------------------------------------------------------------------
def dump_database(target_dir, stamp):
    db = settings.DATABASES["default"]
    engine = db["ENGINE"]

    if "postgresql" in engine:
        path = Path(target_dir) / f"iqmath_db_{stamp}.dump"
        env = dict(os.environ, PGPASSWORD=str(db.get("PASSWORD") or ""))
        cmd = [
            config.PG_DUMP_BIN,
            "-h", str(db.get("HOST") or "localhost"),
            "-p", str(db.get("PORT") or "5432"),
            "-U", str(db.get("USER") or ""),
            "-Fc",  # siqilgan format, pg_restore bilan tiklanadi
            "-f", str(path),
            str(db["NAME"]),
        ]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump xatosi: {result.stderr.strip()[:500]}")
        return path

    if "sqlite3" in engine:
        path = Path(target_dir) / f"iqmath_db_{stamp}.sqlite3"
        source = sqlite3.connect(str(db["NAME"]))
        dest = sqlite3.connect(str(path))
        with dest:
            source.backup(dest)  # ishlab turgan bazadan ham to'g'ri nusxa oladi
        source.close()
        dest.close()
        return path

    raise RuntimeError(f"Bu baza turi qo'llab-quvvatlanmaydi: {engine}")


# ---------------------------------------------------------------------------
# Fayllar (kitoblar, rasmlar, ...)
# ---------------------------------------------------------------------------
def _iter_media_files(since_ts=None):
    for name in config.MEDIA_DIRS:
        root = config.PROJECT_DIR / name
        if not root.is_dir():
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
                path = Path(dirpath) / filename
                try:
                    if since_ts is None or path.stat().st_mtime > since_ts:
                        yield path
                except OSError:
                    continue


def archive_media(target_dir, stamp, since_ts):
    """(arxiv yo'li yoki None, fayllar soni). Rasm/pdf/video allaqachon siqilgan — tar siqilmaydi."""
    kind = "incr" if since_ts else "full"
    path = Path(target_dir) / f"iqmath_media_{kind}_{stamp}.tar"
    count = 0
    with tarfile.open(path, "w") as tar:
        for file_path in _iter_media_files(since_ts):
            try:
                tar.add(file_path, arcname=str(file_path.relative_to(config.PROJECT_DIR)))
                count += 1
            except OSError as exc:
                logger.warning("Backupga qo'shilmadi %s: %s", file_path, exc)
    if count == 0:
        path.unlink(missing_ok=True)
        return None, 0
    return path, count


# ---------------------------------------------------------------------------
# Yuborish
# ---------------------------------------------------------------------------
def send_file_in_parts(path, label):
    """Faylni bo'laklarga bo'lib barcha admin chatlarga yuboradi. Bo'laklar sonini qaytaradi."""
    size = path.stat().st_size
    total = max(1, -(-size // config.PART_SIZE))
    first_chat, other_chats = config.ADMIN_CHAT_IDS[0], config.ADMIN_CHAT_IDS[1:]

    with open(path, "rb") as fh:
        for index in range(1, total + 1):
            chunk = fh.read(config.PART_SIZE)
            name = path.name if total == 1 else f"{path.name}.part{index:03d}"
            caption = f"{label} — {index}/{total}"
            result = send_document(first_chat, name, chunk, caption)
            # Boshqa adminlarga qayta yuklamasdan, file_id orqali
            file_id = (result.get("document") or {}).get("file_id")
            for chat_id in other_chats:
                try:
                    resend_document(chat_id, file_id, caption)
                except TelegramError as exc:
                    logger.error("Backup bo'lagi %s ga yuborilmadi: %s", chat_id, exc)
            time.sleep(1)  # Telegram cheklovlariga tushmaslik uchun
    return total


def _acquire_lock():
    try:
        if LOCK_FILE.exists() and time.time() - LOCK_FILE.stat().st_mtime > LOCK_STALE_SECONDS:
            LOCK_FILE.unlink()  # oldingi backup qulab qolgan
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False


def run_backup(force_full=False):
    if not config.BOT_TOKEN or not config.ADMIN_CHAT_IDS:
        logger.warning("Backup: TELEGRAM_BOT_TOKEN yoki TELEGRAM_ADMIN_CHAT_IDS yozilmagan")
        return False
    if not _acquire_lock():
        logger.warning("Backup: oldingi backup hali tugamagan")
        return False

    started_ts = time.time()
    now = timezone.localtime()
    stamp = now.strftime("%Y-%m-%d_%H%M")
    tmp_dir = tempfile.mkdtemp(prefix="iqmath_backup_", dir=config.TMP_DIR)

    try:
        last_media_ts = state.load().get("last_media_backup_ts")
        full = force_full or config.MEDIA_MODE == "full" or not last_media_ts or now.weekday() == 6
        since_ts = None if full else last_media_ts

        db_path = dump_database(tmp_dir, stamp)
        media_path, media_count = archive_media(tmp_dir, stamp, since_ts)

        files = [(db_path, "🗄 Baza")]
        if media_path:
            files.append((media_path, "🖼 Fayllar"))

        lines = [
            f"💾 <b>IQMATH backup — {now.strftime('%d.%m.%Y %H:%M')}</b>",
            "",
            f"🗄 Baza: <code>{db_path.name}</code> — {_human(db_path.stat().st_size)}",
        ]
        if media_path:
            since_text = (
                "hammasi" if since_ts is None
                else "o'zgarganlari, " + datetime.fromtimestamp(since_ts).strftime("%d.%m.%Y %H:%M") + " dan beri"
            )
            lines.append(
                f"🖼 Fayllar ({since_text}): {media_count} ta — {_human(media_path.stat().st_size)}"
            )
        else:
            lines.append("🖼 Fayllar: oxirgi backupdan beri yangi fayl yo'q")
        lines.append("")
        for path, _label in files:
            parts = max(1, -(-path.stat().st_size // config.PART_SIZE))
            lines.append(f"<code>{path.name}</code>: {parts} bo'lak\nSHA256: <code>{_sha256(path)}</code>")
        lines += [
            "",
            "♻️ Tiklash: bo'laklarni ketma-ket birlashtiring",
            "<code>cat FAYL.part* &gt; FAYL</code> (Windows: <code>copy /b FAYL.part001+FAYL.part002 FAYL</code>)",
            "Baza: <code>pg_restore --clean --no-owner -d BAZA FAYL.dump</code>",
            "Fayllar: <code>tar -xf FAYL.tar</code> (loyiha papkasida)",
        ]
        broadcast(config.ADMIN_CHAT_IDS, "\n".join(lines))

        for path, label in files:
            send_file_in_parts(path, label)

        # Keyingi incremental backup shu vaqtdan keyin o'zgarganlarni oladi
        state.save(last_media_backup_ts=started_ts, last_backup_at=now.isoformat())
        broadcast(config.ADMIN_CHAT_IDS, "✅ Backup to'liq yuborildi.")
        return True
    except Exception as exc:  # noqa: BLE001 — admin xatoni albatta ko'rishi kerak
        logger.exception("Backup xatosi")
        broadcast(config.ADMIN_CHAT_IDS, f"❌ <b>Backup xatosi</b>\n<code>{html.escape(str(exc)[:3000])}</code>")
        return False
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        LOCK_FILE.unlink(missing_ok=True)
