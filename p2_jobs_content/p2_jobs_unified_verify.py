"""
Verification script for the multi-source unified pipeline. Checks
structural invariants (including that HTML cleaning actually happened —
the bug this script exists partly because of), history-field sanity,
and cross-checks samples against each source's live data.

Run after p2_jobs_multisource_pipeline.py.
"""
import json
import random
import re
import sys

import httpx

REMOTIVE_API_URL = 'https://remotive.com/api/remote-jobs'
ARBEITNOW_API_URL = 'https://www.arbeitnow.com/api/job-board-api'
SAMPLE_SIZE_PER_SOURCE = 5
HTML_TAG_RE = re.compile(r'<[a-zA-Z/][^>]*>')  # a simple "does this look like a tag" check


def load_local_data(path='p2_jobs_unified_data.json') -> list[dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_structural_invariants(records: list[dict]) -> list[str]:
    print('--- Structural checks ---')
    failures = []

    keys = [(r['source'], r['source_id']) for r in records]
    if len(keys) != len(set(keys)):
        failures.append(f'Duplicate (source, source_id) pairs: {len(keys) - len(set(keys))}')
    else:
        print(f'✅ No duplicate (source, source_id) pairs ({len(keys)} records)')

    for field in ('title', 'company', 'url'):
        empty = [r for r in records if not str(r.get(field, '')).strip()]
        if empty:
            failures.append(f'{len(empty)} records with empty "{field}"')
        else:
            print(f'✅ No empty "{field}"')

    valid_sources = {'remotive', 'arbeitnow'}
    bad_sources = [r for r in records if r.get('source') not in valid_sources]
    if bad_sources:
        failures.append(f'{len(bad_sources)} records with unrecognized source value')
    else:
        print(f'✅ All records have a recognized source ({valid_sources})')

    not_bool = [r for r in records if not isinstance(r.get('remote'), bool)]
    if not_bool:
        failures.append(f'{len(not_bool)} records where "remote" is not a boolean')
    else:
        print('✅ "remote" field is boolean on every record')

    html_leftover = [r for r in records if HTML_TAG_RE.search(r.get('description', '') or '')]
    if html_leftover:
        failures.append(f'{len(html_leftover)} records still contain raw HTML tags in "description" — cleaning did not run')
    else:
        print('✅ No raw HTML tags found in "description" (cleaning verified)')

    if 'status' in records[0]:
        bad_status = [r for r in records if r.get('status') not in ('active', 'removed')]
        if bad_status:
            failures.append(f'{len(bad_status)} records with invalid "status" value')
        else:
            print('✅ "status" is a valid value on every record')

        bad_order = [r for r in records if r.get('first_seen_at') and r.get('last_seen_at')
                     and r['first_seen_at'] > r['last_seen_at']]
        if bad_order:
            failures.append(f'{len(bad_order)} records where first_seen_at is AFTER last_seen_at (impossible)')
        else:
            print('✅ first_seen_at <= last_seen_at on every record')

    return failures


def check_remotive_sample(records: list[dict]) -> list[str]:
    remotive_records = [r for r in records if r['source'] == 'remotive']
    if not remotive_records:
        return []
    print(f'\n--- Cross-checking {min(SAMPLE_SIZE_PER_SOURCE, len(remotive_records))} Remotive records ---')
    failures = []
    with httpx.Client(timeout=15) as client:
        resp = client.get(REMOTIVE_API_URL)
        resp.raise_for_status()
        live_by_id = {str(j['id']): j for j in resp.json().get('jobs', [])}

    sample = random.sample(remotive_records, min(SAMPLE_SIZE_PER_SOURCE, len(remotive_records)))
    for record in sample:
        live = live_by_id.get(record['source_id'])
        if live is None:
            print(f"   ℹ️  source_id={record['source_id']}: not in current live sample (expected — small rotating set)")
            continue
        if live.get('title') != record['title']:
            failures.append(f"remotive/{record['source_id']}: title mismatch")
        else:
            print(f"✅ remotive/{record['source_id']}: title matches live source")
    return failures


def check_arbeitnow_sample(records: list[dict]) -> list[str]:
    arbeitnow_records = [r for r in records if r['source'] == 'arbeitnow']
    if not arbeitnow_records:
        return []
    print(f'\n--- Cross-checking {min(SAMPLE_SIZE_PER_SOURCE, len(arbeitnow_records))} Arbeitnow records (page 1 only) ---')
    failures = []
    with httpx.Client(timeout=15) as client:
        resp = client.get(ARBEITNOW_API_URL)
        resp.raise_for_status()
        live_by_slug = {j['slug']: j for j in resp.json().get('data', [])}

    sample = random.sample(arbeitnow_records, min(SAMPLE_SIZE_PER_SOURCE, len(arbeitnow_records)))
    for record in sample:
        live = live_by_slug.get(record['source_id'])
        if live is None:
            print(f"   ℹ️  source_id={record['source_id']}: not on live page 1 (expected — only checking 1 of several pages)")
            continue
        if live.get('title') != record['title']:
            failures.append(f"arbeitnow/{record['source_id']}: title mismatch")
        else:
            print(f"✅ arbeitnow/{record['source_id']}: title matches live source")
    return failures


def run_verification(data: list[dict]) -> bool:
    """Runs all checks against an in-memory dataset (no file re-read) and
    returns True if everything passed. Importable so a pipeline script can
    call this automatically as its last step — one command, fetch through
    verify — instead of requiring a second manual invocation."""
    print('\n========== VERIFICATION ==========')
    all_failures = []
    all_failures += check_structural_invariants(data)
    all_failures += check_remotive_sample(data)
    all_failures += check_arbeitnow_sample(data)

    print('\n=== Verification Summary ===')
    if all_failures:
        print(f'❌ {len(all_failures)} issue(s) found:')
        for f in all_failures:
            print(f'   - {f}')
        return False
    else:
        print('✅ All checks passed — output looks accurate.')
        return True


if __name__ == '__main__':
    # Standalone use: python p2_jobs_unified_verify.py (re-verifies the last
    # saved file without re-running the whole pipeline)
    data = load_local_data()
    print(f'Loaded {len(data)} records from p2_jobs_unified_data.json\n')
    passed = run_verification(data)
    sys.exit(0 if passed else 1)
