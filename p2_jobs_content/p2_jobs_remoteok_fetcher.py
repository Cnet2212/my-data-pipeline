"""
Third job source: RemoteOK public API.

Per RemoteOK's own terms (embedded as the first array element in every
response — not a job, a notice), usage requires linking back to the
specific job's RemoteOK URL and crediting "Remote OK" as source. Handled
in the dashboard via a link column, same pattern as Remotive's attribution.
"""
import httpx

from p2_jobs_cache import get_cached, set_cached

API_URL = 'https://remoteok.com/api'
CACHE_TTL_SECONDS = 60 * 60  # 1 hour — no stated hard quota, but no reason to hammer it


def _fetch_from_network() -> list[dict]:
    headers = {'User-Agent': 'portfolio-demo-fetcher (contact: your-email)'}
    resp = httpx.get(API_URL, headers=headers, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    # The first element is always a ToS/legal notice, not a job — filter
    # to only entries that actually look like postings.
    return [item for item in payload if 'id' in item and 'position' in item]


def fetch_remoteok_jobs() -> list[dict]:
    cached = get_cached('remoteok', CACHE_TTL_SECONDS)
    if cached is not None:
        return cached
    jobs = _fetch_from_network()
    set_cached('remoteok', jobs)
    return jobs
