"""
Lightweight file-based cache with TTL, plus a rolling-window quota tracker.

Real APIs often state usage limits in plain English ("no more than 4 times
a day") rather than enforcing them with an HTTP 429 response — respecting
that requires the CLIENT to self-limit. This module handles both: caching
so repeat runs within the TTL don't hit the network at all, and a quota
tracker that refuses a call (falling back to stale cache if available)
once the stated limit is reached.
"""
import json
import time
from pathlib import Path

CACHE_DIR = Path('.p2_cache')
CACHE_DIR.mkdir(exist_ok=True)


def _cache_path(name: str) -> Path:
    return CACHE_DIR / f'{name}_cache.json'


def get_cached(name: str, ttl_seconds: float):
    """Returns cached data if present and within ttl_seconds, else None."""
    path = _cache_path(name)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding='utf-8'))
    age = time.time() - payload['cached_at']
    if age > ttl_seconds:
        return None
    print(f'💾 Using cached "{name}" data ({age / 60:.0f} min old, TTL {ttl_seconds / 60:.0f} min) — no network call made.')
    return payload['data']


def get_stale_cache(name: str):
    """Returns cached data regardless of age — last-resort fallback when
    quota is exhausted and we'd rather serve old data than no data."""
    path = _cache_path(name)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding='utf-8'))
    age_hours = (time.time() - payload['cached_at']) / 3600
    print(f'⚠️  Serving STALE cached "{name}" data ({age_hours:.1f}h old) — quota exhausted, this is a fallback.')
    return payload['data']


def set_cached(name: str, data) -> None:
    path = _cache_path(name)
    path.write_text(json.dumps({'cached_at': time.time(), 'data': data}, ensure_ascii=False), encoding='utf-8')


def _quota_path(name: str) -> Path:
    return CACHE_DIR / f'{name}_quota.json'


def check_and_record_quota(name: str, daily_limit: int, window_seconds: float = 86400) -> bool:
    """Returns True (and records the call) if under the rolling-window
    quota, False if the limit is already reached."""
    path = _quota_path(name)
    now = time.time()
    calls = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    calls = [t for t in calls if now - t < window_seconds]  # drop calls outside the window

    if len(calls) >= daily_limit:
        oldest = min(calls)
        wait_min = (window_seconds - (now - oldest)) / 60
        print(f'🚫 Quota reached for "{name}": {len(calls)}/{daily_limit} calls in the last '
              f'{window_seconds / 3600:.0f}h. Next call available in ~{wait_min:.0f} min.')
        return False

    calls.append(now)
    path.write_text(json.dumps(calls), encoding='utf-8')
    print(f'✅ Quota check for "{name}": {len(calls)}/{daily_limit} calls used in the last {window_seconds / 3600:.0f}h')
    return True
