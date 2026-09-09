"""
Second real job source: Arbeitnow public API. Different schema from
Remotive (slug instead of numeric id, no salary field, unix timestamp
instead of ISO string, description contains raw HTML) — this file
only fetches and returns RAW records; normalization happens in
p2_jobs_normalize.py so each source stays independently swappable.
"""
import time

import httpx

from p2_jobs_cache import get_cached, set_cached

API_URL = 'https://www.arbeitnow.com/api/job-board-api'
MAX_PAGES = 3         # 250 jobs/page -> up to 750 jobs; raise if you want more
REQUEST_DELAY = 0.5   # politeness delay between pages, per Arbeitnow's "please don't abuse" terms

# Arbeitnow's own docs state data is "updated every hour" — no point
# re-fetching more often than that.
CACHE_TTL_SECONDS = 60 * 60


def _fetch_from_network() -> list[dict]:
    raw_jobs: list[dict] = []
    url = API_URL
    headers = {'User-Agent': 'portfolio-demo-fetcher (contact: your-email)'}

    with httpx.Client(headers=headers, timeout=15) as client:
        for page_num in range(1, MAX_PAGES + 1):
            if not url:
                break
            resp = client.get(url)
            resp.raise_for_status()
            payload = resp.json()

            page_jobs = payload.get('data', [])
            raw_jobs.extend(page_jobs)
            print(f'   📄 Arbeitnow page {page_num}: {len(page_jobs)} jobs')

            url = payload.get('links', {}).get('next')
            if url:
                time.sleep(REQUEST_DELAY)

    return raw_jobs


def fetch_arbeitnow_jobs() -> list[dict]:
    cached = get_cached('arbeitnow', CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    raw_jobs = _fetch_from_network()
    set_cached('arbeitnow', raw_jobs)
    return raw_jobs


if __name__ == '__main__':
    # Standalone smoke test — normally called from p2_jobs_multisource_pipeline.py
    jobs = fetch_arbeitnow_jobs()
    print(f'✅ Fetched {len(jobs)} raw Arbeitnow jobs.')
