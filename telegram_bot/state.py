"""Bot holati (oxirgi yuborilgan o'quvchi, oxirgi backup vaqti) — kichik JSON fayl."""
import json

from .config import STATE_FILE


def load():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def save(**values):
    data = load()
    data.update(values)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)
