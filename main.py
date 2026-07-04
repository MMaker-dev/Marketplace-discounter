import os

from dotenv import load_dotenv

from price_history import get_average_30days, update_price
from sent_tracker import is_already_sent, load_sent_ids, save_sent_ids
from telegram_poster import send_to_telegram
from wb_parser import fetch_wb_discounts


def main():
    load_dotenv()

    token = os.getenv("TELEGRAM_TOKEN")
    channel_id = os.getenv("CHANNEL_ID")

    if not token or not channel_id:
        print("Ошибка: TELEGRAM_TOKEN и CHANNEL_ID должны быть заданы в .env")
        return

    products = fetch_wb_discounts(
        query="menu_v3_9463 смартфон",
        min_discount=40,
        min_rating=4.5,
        min_reviews=50,
        max_pages=2,
    )

    for i, product in enumerate(products[:3]):
        print(i, product)

    found = len(products)
    sent_count = 0
    skipped = 0

    for product in products:
        product_id = str(product["id"])
        sale_price = product["sale_price"]

        update_price(product_id, sale_price)

        print(f"Товар {product.get('name')}: уже отправлен = {is_already_sent(product.get('id'))}")
        if is_already_sent(product_id):
            skipped += 1
            continue

        avg = get_average_30days(product_id)

        if avg is None:
            should_send = True
        else:
            discount_vs_avg = (1 - sale_price / avg) * 100
            should_send = discount_vs_avg >= 40

        if not should_send:
            skipped += 1
            continue

        sent = send_to_telegram(product, token, channel_id, avg_price=avg)
        print(f"Результат отправки: {sent}")
        if not sent:
            print(f"Ошибка отправки для {product.get('name')}")
        if sent:
            save_sent_ids(product_id)
            sent_count += 1
        else:
            skipped += 1

    print(f"Найдено: {found}, отправлено: {sent_count}, пропущено: {skipped}")


if __name__ == "__main__":
    main()
