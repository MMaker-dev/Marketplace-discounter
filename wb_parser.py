import os
import random
import time
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

load_dotenv()

SEARCH_BASE_URL = (
    "https://www.wildberries.ru/__internal/u-search/exactmatch/ru/common/v18/search"
)

SEARCH_PARAMS = {
    "ab_testing": "false",
    "appType": "1",
    "curr": "rub",
    "dest": "-1257786",
    "hide_dtype": "15",
    "hide_vflags": "4294967296",
    "lang": "ru",
    "locale": "ru",
    "resultset": "catalog",
    "sort": "popular",
    "spp": "30",
    "suppressSpellcheck": "false",
}


def _image_url(item: dict) -> str:
    images = item.get("images")
    if isinstance(images, list) and images:
        first = images[0]
        return first if isinstance(first, str) else str(first)

    product_id = item.get("id")
    pics = item.get("pics")
    if product_id and pics:
        return f"https://images.wb.ru/c516x688/new/{product_id}/1.jpg"
    return ""


def _resolve_prices(product: dict) -> tuple[int | None, int | None]:
    price_u = product.get("priceU")
    sale_price_u = product.get("salePriceU")
    if price_u and sale_price_u:
        return price_u, sale_price_u

    sizes = product.get("sizes")
    if sizes and len(sizes) > 0 and isinstance(sizes[0], dict):
        price = sizes[0].get("price")
        if isinstance(price, dict):
            basic = price.get("basic")
            product_price = price.get("product")
            if basic and product_price:
                return basic, product_price

    return None, None


def _extract_products(data: dict) -> list:
    if not isinstance(data, dict):
        return []

    inner = data.get("data")
    inner = inner if isinstance(inner, dict) else {}

    for products in (
        inner.get("products"),
        data.get("products"),
        inner.get("productCards"),
        data.get("items"),
    ):
        if products and isinstance(products, list):
            return products

    return []


def _fetch_page(query: str, page: int) -> dict | None:
    params = {
        **SEARCH_PARAMS,
        "query": query,
        "page": str(page),
    }
    url = f"{SEARCH_BASE_URL}?{urlencode(params)}"

    headers = {
        "accept": "*/*",
        "accept-language": "ru,en;q=0.9",
        "Cookie": os.getenv("WB_COOKIE", ""),
        "deviceid": "site_c1fed39ac6de4044aafdd627b8af853a",
        "priority": "u=1, i",
        "referer": (
            "https://www.wildberries.ru/catalog/elektronika/"
            "smartfony-i-telefony/vse-smartfony"
        ),
        "sec-ch-ua": (
            '"Chromium";v="146", "Not-A.Brand";v="24", "YaBrowser";v="26.4", '
            '"Yowser";v="2.5"'
        ),
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/146.0.0.0 YaBrowser/26.4.0.0 Safari/537.36"
        ),
        "x-queryid": os.getenv("WB_X_QUERYID", ""),
        "x-requested-with": "XMLHttpRequest",
        "x-spa-version": "14.16.0",
        "x-userid": "0",
    }

    for attempt in range(3):
        response = requests.get(url, headers=headers, timeout=30)
        print("URL:", response.url)
        print("Response text:", response.text[:500])
        print(f"Статус ответа: {response.status_code}")

        if response.status_code in (403, 429):
            if attempt < 2:
                time.sleep(60)
                continue
            return None

        response.raise_for_status()
        data = response.json()

        print("Keys in response:", list(data.keys()))
        if "data" in data:
            print("Keys in data:", list(data["data"].keys()))
            print("Number of products:", len(data["data"].get("products", [])))
        else:
            print("No 'data' key in response")

        print("Type of data['data']:", type(data.get("data")))
        print("Keys in data['data']:", list(data.get("data", {}).keys()))
        products_raw = _extract_products(data)
        print("Type of products_raw:", type(products_raw))
        print("Length of products_raw:", len(products_raw))
        if products_raw:
            print("First product keys:", list(products_raw[0].keys()))

        products = _extract_products(data)
        print(f"Количество товаров в ответе: {len(products)}")
        if products:
            print(products[0])
        return data

    return None


def fetch_wb_discounts(
    query="смартфон",
    min_discount=40,
    min_rating=4.5,
    min_reviews=50,
    max_pages=2,
):
    results = []

    for page in range(1, max_pages + 1):
        if page > 1:
            time.sleep(random.uniform(3, 6))

        payload = _fetch_page(query, page)
        if not payload:
            continue

        products = _extract_products(payload)
        if not products:
            break

        for product in products:
            original_price_u, sale_price_u = _resolve_prices(product)

            if not original_price_u or not sale_price_u:
                continue
            if original_price_u <= sale_price_u:
                continue

            sale = product.get("sale")
            if sale is not None:
                discount = sale
            else:
                discount = round(100 - (sale_price_u / original_price_u * 100), 1)

            rating = product.get("reviewRating") or product.get("rating") or 0
            feedbacks = product.get("feedbacks") or product.get("nmFeedbacks") or 0

            if discount < min_discount:
                continue
            if rating < min_rating:
                continue
            if feedbacks < min_reviews:
                continue
            if original_price_u / sale_price_u > 3:
                continue

            product_id = product.get("id")
            if not product_id:
                continue

            results.append(
                {
                    "id": product_id,
                    "name": product.get("name", ""),
                    "sale_price": round(sale_price_u / 100),
                    "original_price": round(original_price_u / 100),
                    "discount": int(round(discount)),
                    "rating": rating,
                    "reviews": feedbacks,
                    "image_url": _image_url(product),
                    "product_url": (
                        f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"
                    ),
                }
            )

    results.sort(key=lambda x: x["discount"], reverse=True)
    return results
