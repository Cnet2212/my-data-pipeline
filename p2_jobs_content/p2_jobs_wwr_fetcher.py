"""
Fourth job source: We Work Remotely's public RSS feed.

RSS is a syndication format BY DESIGN — aggregating it isn't a scraping
technique, it's literally the format's intended use. The feed itself
declares <ttl>60</ttl> (minutes) — a standard RSS element meaning "don't
refetch more often than this" — so the cache TTL below honors that
instead of picking an arbitrary number.
"""
import xml.etree.ElementTree as ET

import httpx

from p2_jobs_cache import get_cached, set_cached

RSS_URL = 'https://weworkremotely.com/remote-jobs.rss'
CACHE_TTL_SECONDS = 60 * 60  # matches the feed's own declared <ttl>60</ttl>


def _fetch_from_network() -> list[dict]:
    headers = {'User-Agent': 'portfolio-demo-fetcher (contact: your-email)'}
    resp = httpx.get(RSS_URL, headers=headers, timeout=15)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    jobs = []
    for item in root.findall('.//item'):
        title_text = (item.findtext('title') or '').strip()
        # Observed title format: "Company: Position"
        if ':' in title_text:
            company, _, position = title_text.partition(':')
            company, position = company.strip(), position.strip()
        else:
            company, position = 'Unknown', title_text

        jobs.append({
            'company': company,
            'position': position,
            'region': item.findtext('region') or '',
            'category': item.findtext('category') or '',
            'job_type': item.findtext('type') or '',
            'link': item.findtext('link') or '',
            'guid': item.findtext('guid') or item.findtext('link') or '',
            'description': item.findtext('description') or '',
            'pub_date': item.findtext('pubDate') or '',
        })
    return jobs


def fetch_wwr_jobs() -> list[dict]:
    cached = get_cached('weworkremotely', CACHE_TTL_SECONDS)
    if cached is not None:
        return cached
    jobs = _fetch_from_network()
    set_cached('weworkremotely', jobs)
    return jobs
