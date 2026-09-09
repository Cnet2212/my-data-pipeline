"""
Project 2: Real job listings via Remotive's official public API.

Remotive (remotive.com) publishes remote job listings and explicitly
provides this endpoint for third-party use — no auth, no key required.
Docs: https://remotive.com/api/remote-jobs (see remotive.com/api-doc)

This is intentionally the simplest project of the four: a single clean
HTTP call, validated and stored. Recognizing when NOT to add retry loops,
pagination, or concurrency is as much a real skill as knowing how to build
them — most of the complexity in projects 1/3/4 would be wasted effort here.
"""
import json

import httpx
from pydantic import BaseModel, Field

from p2_jobs_cache import get_cached, get_stale_cache, set_cached, check_and_record_quota

API_URL = 'https://remotive.com/api/remote-jobs'

# NOTE: Remotive's free public API caps results at a small fixed sample
# (confirmed via the API's own "total-job-count" field — full access is a
# paid tier). Per Remotive's API terms: max ~4 requests/day. Data barely
# changes faster than that anyway, so a 6h cache TTL naturally keeps us
# within quota under normal use (4 runs spaced through a day).
CACHE_TTL_SECONDS = 6 * 60 * 60
DAILY_QUOTA = 4


class JobItem(BaseModel):
    id: int
    title: str = Field(min_length=1)
    company: str
    category: str
    job_type: str
    location: str
    salary: str = ''
    url: str
    published_at: str
    tags: list[str] = Field(default_factory=list)


def _fetch_from_network() -> list[dict]:
    headers = {'User-Agent': 'portfolio-demo-fetcher (contact: your-email)'}
    with httpx.Client(headers=headers, timeout=15) as client:
        resp = client.get(API_URL)
        resp.raise_for_status()
        payload = resp.json()
    return payload.get('jobs', [])


def fetch_jobs() -> list[dict]:
    raw_jobs = get_cached('remotive', CACHE_TTL_SECONDS)

    if raw_jobs is None:
        if check_and_record_quota('remotive', DAILY_QUOTA):
            raw_jobs = _fetch_from_network()
            set_cached('remotive', raw_jobs)
        else:
            # Quota exhausted — better to serve old data than none at all,
            # but the caller should know it might be stale.
            raw_jobs = get_stale_cache('remotive') or []

    print(f'🔎 Working with {len(raw_jobs)} raw job postings.')

    validated = []
    for job in raw_jobs:
        try:
            item = JobItem(
                id=job['id'],
                title=job.get('title', ''),
                company=job.get('company_name', 'Unknown'),
                category=job.get('category', 'Unknown'),
                job_type=job.get('job_type', 'Unknown'),
                location=job.get('candidate_required_location', 'Unknown'),
                salary=job.get('salary') or '',
                url=job.get('url', ''),
                published_at=job.get('publication_date', ''),
                tags=job.get('tags', []),
            )
            validated.append(item.model_dump())
        except Exception as e:
            print(f'⚠️ [Circuit Breaker] Skipped invalid record (id={job.get("id")}): {e}')

    return validated


if __name__ == '__main__':
    data = fetch_jobs()
    print(f'✅ Validated {len(data)} job listings.')

    try:
        from p2_jobs_db import save_jobs_to_db
        result = save_jobs_to_db(data)
        if result:
            print(f'☁️  Upserted {len(data)} records to Supabase.')
    except RuntimeError as e:
        print(f'ℹ️  Skipping Supabase save: {e}')

    with open('p2_jobs_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('💾 Saved p2_jobs_data.json')
