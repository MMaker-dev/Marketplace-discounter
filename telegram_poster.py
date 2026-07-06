import os
import time
from io import BytesIO

import requests
from dotenv import load_dotenv

load_dotenv()

PROXY_BASE = "https://wb-proxy.nikon6233.workers.dev/?url="

WB_IMAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/146.0.0.0 YaBrowser/26.4.0.0 Safari/537.36"
    ),
    "Referer": "https://www.wildberries.ru/",
    "Accept": "image/webp,image/*,*/*",
}


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


def _log_telegram_error(response: requests.Response) -> None:
    if response.status_code != 200:
        print(f"Telegram API error: {response.status_code} {response.text}")


def _send_message(token: str, payload: dict, caption: str) -> bool:
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data={**payload, "text": caption},
        timeout=30,
    )
    _log_telegram_error(response)
    return response.ok


def _send_photo_file(
    token: str, payload: dict, caption: str, image_data: BytesIO
) -> bool:
    image_data.seek(0)
    print("Отправляю фото в Telegram...")
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data={**payload, "caption": caption},
        files={"photo": ("photo.jpg", image_data, "image/jpeg")},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"Ошибка Telegram при отправке фото: {resp.status_code} {resp.text}")
    return resp.ok


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
            proxy_url = f"{PROXY_BASE}{image_url}"
            print(f"Пытаюсь скачать фото через прокси: {proxy_url}")
            headers = {
                **WB_IMAGE_HEADERS,
                "Cookie": os.getenv("WB_COOKIE", ""),
                "x-queryid": os.getenv("WB_X_QUERYID", ""),
            }
            img_response = requests.get(proxy_url, headers=headers, timeout=30)
            print(f"Статус ответа прокси: {img_response.status_code}")
            print(f"Content-Type ответа: {img_response.headers.get('Content-Type')}")
            print(f"Длина контента: {len(img_response.content)} байт")
            if img_response.ok and img_response.content:
                image_data = BytesIO(img_response.content)
                img_data = image_data.getvalue()
                print(f"Фото скачано успешно, размер {len(img_data)} байт")
                sent = _send_photo_file(token, payload, caption, image_data)

        if not sent:
            if image_url:
                print("Фото не отправлено, перехожу к тексту")
            sent = _send_message(token, payload, caption)
    except requests.RequestException as e:
        print(f"Ошибка скачивания фото: {e}")
        sent = False

    _send_delay()
    return sent
