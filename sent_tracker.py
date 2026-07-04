import json
from datetime import datetime
from pathlib import Path

SENT_FILE = Path(__file__).parent / "sent_ids.json"


def _load_entries() -> list:
    try:
        if not SENT_FILE.exists():
            return []
        with open(SENT_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return []


def _write_entries(entries: list) -> None:
    try:
        with open(SENT_FILE, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    except (OSError, TypeError, ValueError):
        pass


def load_sent_ids() -> set:
    entries = _load_entries()
    ids = set()
    for entry in entries:
        if isinstance(entry, dict) and "id" in entry:
            ids.add(str(entry["id"]))
    return ids


def save_sent_ids(product_id: str) -> None:
    product_id = str(product_id)
    entries = _load_entries()

    for entry in entries:
        if isinstance(entry, dict) and str(entry.get("id")) == product_id:
            return

    entries.append(
        {
            "id": product_id,
            "date": datetime.today().strftime("%Y-%m-%d"),
        }
    )
    _write_entries(entries)


def is_already_sent(product_id: str) -> bool:
    return str(product_id) in load_sent_ids()
