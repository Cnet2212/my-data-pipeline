"""
Project 1 (real-world variant): live content aggregation from Hacker News.

Hacker News publishes an official public API (Firebase-backed) specifically
so third parties can build on top of their data — this is not a workaround,
it's the intended integration path. No auth, no key, generous rate limits.

Docs: https://github.com/HackerNews/API

Technique highlight: instead of fetching story details one-by-one (slow),
we fetch them CONCURRENTLY with a semaphore capping how many requests are
in flight at once. This is the realistic pattern for pulling many records
from an API efficiently while still being a good citizen.
"""
import asyncio
import json
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel, Field

TOP_STORIES_URL = 'https://hacker-news.firebaseio.com/v0/topstories.json'
ITEM_URL = 'https://hacker-news.firebaseio.com/v0/item/{}.json'
MAX_STORIES = 100   # how many of the current top stories to pull
CONCURRENCY = 10    # max simultaneous in-flight requests


class HNStory(BaseModel):
    id: int
    title: str = Field(min_length=1)
    url: str | None = None
    score: int = Field(ge=0)
    author: str
    num_comments: int = Field(ge=0)
    posted_at: str


async def fetch_item(client: httpx.AsyncClient, sem: asyncio.Semaphore, story_id: int) -> dict | None:
    async with sem:
        for attempt in range(1, 4):
            try:
                resp = await client.get(ITEM_URL.format(story_id), timeout=10)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                if attempt == 3:
                    print(f'   ⚠️ Giving up on story {story_id} after 3 attempts: {e}')
                    return None
                await asyncio.sleep(1.5 ** attempt)


async def scrape_hn_top_stories() -> list[dict]:
    async with httpx.AsyncClient(headers={'User-Agent': 'portfolio-demo-scraper (contact: your-email)'}) as client:
        resp = await client.get(TOP_STORIES_URL, timeout=10)
        resp.raise_for_status()
        story_ids = resp.json()[:MAX_STORIES]
        print(f'🔎 Fetching {len(story_ids)} live top stories from Hacker News ...')

        sem = asyncio.Semaphore(CONCURRENCY)
        tasks = [fetch_item(client, sem, sid) for sid in story_ids]
        raw_items = await asyncio.gather(*tasks)

    validated = []
    for item in raw_items:
        if not item or item.get('type') != 'story':
            continue
        try:
            record = HNStory(
                id=item['id'],
                title=item.get('title', ''),
                url=item.get('url'),
                score=item.get('score', 0),
                author=item.get('by', 'unknown'),
                num_comments=item.get('descendants', 0),
                posted_at=datetime.fromtimestamp(item.get('time', 0), tz=timezone.utc).isoformat(),
            )
            validated.append(record.model_dump())
        except Exception as e:
            print(f'⚠️ [Circuit Breaker] Skipped invalid record (id={item.get("id")}): {e}')

    return validated


if __name__ == '__main__':
    data = asyncio.run(scrape_hn_top_stories())
    print(f'✅ Fetched and validated {len(data)} live, real stories from Hacker News.')

    try:
        from p1_hn_db import save_stories_to_db
        result = save_stories_to_db(data)
        if result:
            print(f'☁️  Upserted {len(data)} records to Supabase.')
    except RuntimeError as e:
        print(f'ℹ️  Skipping Supabase save: {e}')

    with open('p1_hn_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('💾 Saved p1_hn_data.json')
