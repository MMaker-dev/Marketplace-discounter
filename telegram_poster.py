import traceback

import requests
import time


def _escape_markdown(text: str) -> str:
    for char in ("_", "*", "`", "["):
        text = text.replace(char, f"\\{char}")
    return text


def _format_price(price: float) -> str:
    if price == int(price):
        return str(int(price))
    return f"{price:.2f}".rstrip("0").rstrip(".")


def _build_caption(product: dict, avg_price: float | None) -> str:
    name = _escape_markdown(str(product.get("name", "")))

    if avg_price is not None:
        price_line = f"💰 Средняя цена за 30 дней: {_format_price(avg_price)} ₽"
    else:
        price_line = f"💰 Старая цена: {product.get('original_price', 0)} ₽"

    sale_price = product.get("sale_price", 0)
    discount = product.get("discount", 0)
    rating = product.get("rating", 0)
    reviews = product.get("reviews", 0)
    product_url = product.get("product_url", "")

    return "\n".join(
        [
            f"🔥 {name}",
            price_line,
            f"✅ Цена сегодня: {sale_price} ₽ (скидка {discount}%)",
            f"⭐ Рейтинг: {rating} ({reviews} отзывов)",
            f"[🔗 Купить на Wildberries]({product_url})",
        ]
    )


def _send_delay() -> None:
    time.sleep(1 + (time.monotonic() % 1))


def send_to_telegram(
    product: dict,
    token: str,
    channel_id: str,
    avg_price: float = None,
) -> bool:
    caption = _build_caption(product, avg_price)
    payload = {
        "chat_id": channel_id,
        "parse_mode": "Markdown",
    }

    sent = False
    image_url = product.get("image_url")

    try:
        if image_url:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                data={**payload, "photo": image_url, "caption": caption},
                timeout=30,
            )
            if not response.ok:
                print(f"Telegram API error: {response.status_code} {response.text}")
            if response.ok:
                sent = True
            else:
                response = requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    data={**payload, "text": caption},
                    timeout=30,
                )
                if not response.ok:
                    print(f"Telegram API error: {response.status_code} {response.text}")
                sent = response.ok
        else:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data={**payload, "text": caption},
                timeout=30,
            )
            if not response.ok:
                print(f"Telegram API error: {response.status_code} {response.text}")
            sent = response.ok
    except requests.RequestException:
        print("Исключение при отправке:")
        traceback.print_exc()
        sent = False

    _send_delay()
    return sent
