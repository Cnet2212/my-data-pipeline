import asyncio
import json
import re
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field

# 1. Chuẩn Dữ Liệu bằng Pydantic (Data Validation Schema)
class ProductItem(BaseModel):
    title: str = Field(min_length=1)
    price: float = Field(gt=0)
    category: str
    in_stock: bool


# Trang thật để practice scraping (structure ổn định, dùng cho tutorial nhiều năm nay)
CATEGORIES = {
    'Travel': 'https://books.toscrape.com/catalogue/category/books/travel_2/index.html',
    'Mystery': 'https://books.toscrape.com/catalogue/category/books/mystery_3/index.html',
    'Historical Fiction': 'https://books.toscrape.com/catalogue/category/books/historical-fiction_4/index.html',
}


async def scrape_category(page, category_name: str, url: str) -> list[dict]:
    await page.goto(url, wait_until='networkidle')
    books = await page.query_selector_all('article.product_pod')

    items = []
    for book in books:
        title_el = await book.query_selector('h3 a')
        title = await title_el.get_attribute('title')

        price_el = await book.query_selector('p.price_color')
        price_text = await price_el.inner_text()
        price = float(re.sub(r'[^\d.]', '', price_text))  # bỏ ký hiệu tiền tệ

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


async def scrape_data_pipeline() -> list[dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Chặn ảnh để tăng tốc — không chặn CSS/font vì không cần thiết cho việc đọc selector
        await page.route('**/*.{png,jpg,jpeg,gif}', lambda route: route.abort())

        raw_items = []
        for name, url in CATEGORIES.items():
            print(f'🔎 Đang crawl category: {name} ...')
            raw_items.extend(await scrape_category(page, name, url))

        await browser.close()

        # 2. Circuit Breaker: kiểm tra dữ liệu thô trước khi lưu
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

    # Đẩy lên Supabase nếu đã set biến môi trường SUPABASE_URL / SUPABASE_KEY
    try:
        from db import save_products_to_db
        result = save_products_to_db(data)
        if result:
            print(f'☁️  Đã upsert {len(data)} records lên Supabase.')
    except RuntimeError as e:
        print(f'ℹ️  Bỏ qua bước lưu Supabase: {e}')

    # Lưu ra file local để app.py dùng thử ngay, chưa cần setup Supabase vội
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('💾 Đã lưu data.json — bạn có thể mở file này ra xem trước khi setup Supabase.')
