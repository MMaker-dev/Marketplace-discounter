import json
from datetime import datetime, timedelta
from pathlib import Path

HISTORY_FILE = Path(__file__).parent / "price_history.json"


def load_history() -> dict:
    try:
        if not HISTORY_FILE.exists():
            return {}
        with open(HISTORY_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return {}


def save_history(history: dict) -> None:
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except (OSError, TypeError, ValueError):
        pass


def update_price(product_id: str, price: float, date: str = None) -> None:
    if date is None:
        date = datetime.today().strftime("%Y-%m-%d")

    history = load_history()
    product_key = str(product_id)

    if product_key not in history or not isinstance(history[product_key], dict):
        history[product_key] = {"dates": {}}
    elif "dates" not in history[product_key] or not isinstance(
        history[product_key]["dates"], dict
    ):
        history[product_key]["dates"] = {}

    history[product_key]["dates"][date] = float(price)
    save_history(history)


def get_average_30days(product_id: str) -> float | None:
    history = load_history()
    product_data = history.get(str(product_id))
    if not isinstance(product_data, dict):
        return None

    dates = product_data.get("dates")
    if not isinstance(dates, dict) or not dates:
        return None

    today = datetime.today().date()
    start = today - timedelta(days=30)
    prices = []

    for date_str, value in dates.items():
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d").date()
            price = float(value)
        except (ValueError, TypeError):
            continue
        if start <= day <= today:
            prices.append(price)

    if len(prices) < 7:
        return None

    return sum(prices) / len(prices)
