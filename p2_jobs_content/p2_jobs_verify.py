"""
Verification script for Project 2: checks p2_jobs_data.json against basic
data-quality invariants, and cross-checks a random sample against a fresh
call to the live Remotive API to confirm stored values match the source.

Run this after p2_jobs_fetcher.py.
"""
import json
import random
import sys

import httpx

API_URL = 'https://remotive.com/api/remote-jobs'
SAMPLE_SIZE = 10


def load_local_data(path='p2_jobs_data.json') -> list[dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_structural_invariants(records: list[dict], expected_total: int | None = None) -> list[str]:
    print('--- Structural checks ---')
    failures = []

    ids = [r['id'] for r in records]
    if len(ids) != len(set(ids)):
        failures.append(f'Duplicate ids found: {len(ids) - len(set(ids))} duplicates')
    else:
        print(f'✅ No duplicate ids ({len(ids)} unique records)')

    for field in ('title', 'company', 'category', 'url'):
        empty = [r for r in records if not str(r.get(field, '')).strip()]
        if empty:
            failures.append(f'{len(empty)} records with empty "{field}"')
        else:
            print(f'✅ No empty "{field}"')

    bad_urls = [r for r in records if not r.get('url', '').startswith('http')]
    if bad_urls:
        failures.append(f'{len(bad_urls)} records with malformed url')
    else:
        print('✅ All urls look well-formed')

    # Compare against the source's own reported total instead of a guessed
    # threshold — Remotive's free tier caps this at a small number, so a
    # fixed "expected ~100+" assumption would be a false alarm, not a bug.
    if expected_total is not None:
        if len(records) != expected_total:
            failures.append(f'Record count ({len(records)}) does not match source-reported total ({expected_total})')
        else:
            print(f'✅ Record count matches source-reported total ({expected_total})')

    return failures


def check_against_live_source(records: list[dict], sample_size: int = SAMPLE_SIZE) -> list[str]:
    print(f'\n--- Cross-checking {min(sample_size, len(records))} random records against a fresh live fetch ---')
    failures = []

    with httpx.Client(timeout=15) as client:
        resp = client.get(API_URL)
        resp.raise_for_status()
        live_jobs = {j['id']: j for j in resp.json().get('jobs', [])}

    sample = random.sample(records, min(sample_size, len(records)))
    for record in sample:
        live = live_jobs.get(record['id'])
        if live is None:
            # Listings can be filled/removed between the original fetch and this
            # check — that's expected on a live board, so this is informational.
            print(f"   ℹ️  id={record['id']}: no longer present in live listings (expected — postings expire)")
            continue

        if live.get('title') != record['title']:
            failures.append(
                f"id={record['id']}: title mismatch — stored={record['title']!r} live={live.get('title')!r}"
            )
        elif live.get('company_name') != record['company']:
            failures.append(
                f"id={record['id']}: company mismatch — stored={record['company']!r} live={live.get('company_name')!r}"
            )
        else:
            print(f"✅ id={record['id']}: title and company match live source")

    return failures


if __name__ == '__main__':
    data = load_local_data()
    print(f'Loaded {len(data)} records from p2_jobs_data.json\n')

    # Fetch the source's own reported total for an honest comparison instead
    # of a guessed threshold.
    with httpx.Client(timeout=15) as _client:
        _resp = _client.get(API_URL)
        _resp.raise_for_status()
        expected_total = _resp.json().get('total-job-count')

    all_failures = []
    all_failures += check_structural_invariants(data, expected_total=expected_total)
    all_failures += check_against_live_source(data)

    print('\n=== Summary ===')
    if all_failures:
        print(f'❌ {len(all_failures)} issue(s) found:')
        for f in all_failures:
            print(f'   - {f}')
        sys.exit(1)
    else:
        print('✅ All checks passed — output looks accurate.')
        sys.exit(0)
