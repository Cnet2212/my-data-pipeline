import asyncio
import json
import random
import re
from urllib.parse import urljoin

from playwright.async_api import async_playwright, Page
from pydantic import BaseModel, Field


# 1. Data schema with Pydantic (validation layer)
class ProductItem(BaseModel):
    title: str = Field(min_length=1)
    price: float = Field(gt=0)
    category: str
    in_stock: bool


# Categories with more pages, so pagination is actually exercised
CATEGORIES = {
    'Travel': 'https://books.toscrape.com/catalogue/category/books/travel_2/index.html',
    'Mystery': 'https://books.toscrape.com/catalogue/category/books/mystery_3/index.html',
    'Historical Fiction': 'https://books.toscrape.com/catalogue/category/books/historical-fiction_4/index.html',
    'Fiction': 'https://books.toscrape.com/catalogue/category/books/fiction_10/index.html',
    'Nonfiction': 'https://books.toscrape.com/catalogue/category/books/nonfiction_13/index.html',
    'Sequential Art': 'https://books.toscrape.com/catalogue/category/books/sequential-art_5/index.html',
}

MAX_RETRIES = 3
BACKOFF_BASE = 1.5          # seconds, multiplied exponentially on each retry
DELAY_RANGE = (0.4, 1.2)    # seconds, randomized delay between requests (rate limiting)


async def goto_with_retry(page: Page, url: str, retries: int = MAX_RETRIES) -> None:
    """Navigate to url, retrying with exponential backoff on network/timeout errors."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            await page.goto(url, wait_until='networkidle', timeout=15000)
            return
        except Exception as e:
            last_error = e
            if attempt == retries:
                break
            wait = BACKOFF_BASE ** attempt
            print(f'   ⚠️ Failed to load {url} (attempt {attempt}/{retries}): {e} — retrying in {wait:.1f}s')
            await asyncio.sleep(wait)
    # Retries exhausted — raise so the caller can decide (skip this page, don't crash the whole pipeline)
    raise RuntimeError(f'Could not load {url} after {retries} attempts: {last_error}')


async def parse_current_page(page: Page, category_name: str) -> list[dict]:
    books = await page.query_selector_all('article.product_pod')
    items = []
    for book in books:
        title_el = await book.query_selector('h3 a')
        title = await title_el.get_attribute('title')

        price_el = await book.query_selector('p.price_color')
        price_text = await price_el.inner_text()
        price = float(re.sub(r'[^\d.]', '', price_text))

        stock_el = await book.query_selector('p.instock.availability')
        stock_text = (await stock_el.inner_text()).strip()
        in_stock = 'In stock' in stock_text

        items.append({
            'title': title,
            'price': price,
            'category': category_name,
            'in_stock': in_stock,
        })
    return items


async def scrape_category_with_pagination(page: Page, category_name: str, start_url: str) -> list[dict]:
    """Scrape every page of a category, following the 'next' link until it disappears."""
    items: list[dict] = []
    current_url = start_url
    page_num = 1

    while current_url:
        try:
            await goto_with_retry(page, current_url)
        except RuntimeError as e:
            print(f'   ❌ Skipping page {page_num} of "{category_name}": {e}')
            break

        page_items = await parse_current_page(page, category_name)
        items.extend(page_items)
        print(f'   📄 {category_name} — page {page_num}: {len(page_items)} books')

        # Look for a "next" link — if there isn't one, we've reached the last page
        next_el = await page.query_selector('li.next > a')
        if next_el:
            href = await next_el.get_attribute('href')
            current_url = urljoin(current_url, href)
            page_num += 1
            # Rate limiting: random pause before moving to the next page
            await asyncio.sleep(random.uniform(*DELAY_RANGE))
        else:
            current_url = None

    return items


async def scrape_data_pipeline() -> list[dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.route('**/*.{png,jpg,jpeg,gif}', lambda route: route.abort())

        raw_items = []
        for name, url in CATEGORIES.items():
            print(f'🔎 Crawling category: {name} ...')
            raw_items.extend(await scrape_category_with_pagination(page, name, url))
            await asyncio.sleep(random.uniform(*DELAY_RANGE))  # pause between categories

        await browser.close()

        # 2. Circuit breaker: validate raw records before they're saved
        validated_items = []
        for item in raw_items:
            try:
                valid_item = ProductItem(**item)
                validated_items.append(valid_item.model_dump())
            except Exception as e:
                print(f'⚠️ [Circuit Breaker] Skipped invalid record: {item} | Error: {e}')

        return validated_items


if __name__ == '__main__':
    data = asyncio.run(scrape_data_pipeline())
    print(f'✅ Scraping completed. Validated {len(data)} items successfully.')

    # Push to Supabase if SUPABASE_URL / SUPABASE_KEY are set
    try:
        from db import save_products_to_db
        result = save_products_to_db(data)
        if result:
            print(f'☁️  Upserted {len(data)} records to Supabase.')
    except RuntimeError as e:
        print(f'ℹ️  Skipping Supabase save: {e}')

    # Also save locally so app.py can be tested without Supabase set up yet
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('💾 Saved data.json')
