"""
Verification for Project 4: confirms the LOGIN itself actually succeeded
(not just that requests returned 200), plus shared data-quality checks
and a live cross-check.
"""
import json
import random
import sys

from shared_data_quality import run_data_quality_report
from p4_login_fetcher import login_and_get_session, verify_logged_in, fetch_all_quotes


def load_local_data(path='p4_login_data.json') -> list[dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_login_succeeded() -> list[str]:
    print('--- Login verification ---')
    failures = []
    client = login_and_get_session()
    if verify_logged_in(client):
        print('✅ Session shows "Logout" link — login genuinely succeeded (not just HTTP 200)')
    else:
        failures.append('Login did NOT succeed — "Logout" link not found after posting credentials')
    return failures


def check_against_live_source(records: list[dict]) -> list[str]:
    print('\n--- Cross-checking against live source ---')
    failures = []
    client = login_and_get_session()
    live_records = fetch_all_quotes(client)
    live_by_key = {(r['author'], r['text']): r for r in live_records}

    sample = random.sample(records, min(5, len(records)))
    for record in sample:
        key = (record['author'], record['text'])
        live = live_by_key.get(key)
        if live is None:
            failures.append(f"{record['author']} quote not found in live re-fetch")
            continue
        if set(live['tags']) != set(record['tags']):
            failures.append(f"{record['author']} quote: tags mismatch")
        else:
            print(f"✅ {record['author']}: quote + tags match live source")
    return failures


def run_verification(data: list[dict]) -> bool:
    print('\n========== VERIFICATION ==========')

    dq_report = run_data_quality_report(
        data,
        required_fields=['text', 'author'],
        text_fields=['text', 'author'],
        key_fields=['author', 'text'],
    )
    print(dq_report['summary'])
    for f in dq_report['hard_failures']:
        print(f'   ❌ {f}')
    for w in dq_report['warnings']:
        print(f'   ⚠️  {w}')

    login_failures = check_login_succeeded()
    live_failures = check_against_live_source(data)

    all_failures = dq_report['hard_failures'] + login_failures + live_failures
    print('\n=== Verification Summary ===')
    if all_failures:
        print(f'❌ {len(all_failures)} issue(s) found:')
        for f in all_failures:
            print(f'   - {f}')
        return False
    else:
        print('✅ All checks passed — output looks accurate, and login was genuinely confirmed.')
        return True


if __name__ == '__main__':
    data = load_local_data()
    print(f'Loaded {len(data)} records from p4_login_data.json')
    passed = run_verification(data)
    sys.exit(0 if passed else 1)
