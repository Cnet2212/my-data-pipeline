"""
Verification for Project 3: shared data-quality checks + a live cross-check
against the source (re-fetching one team via the search filter and
comparing against what was stored).
"""
import json
import random
import sys

from shared_data_quality import run_data_quality_report
from p3_hockey_fetcher import fetch_by_team_search


def load_local_data(path='p3_hockey_data.json') -> list[dict]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_against_live_source(records: list[dict]) -> list[str]:
    print('\n--- Cross-checking against live source ---')
    failures = []

    sample_team = random.choice(records)['team_name']
    print(f'   Re-fetching all seasons for "{sample_team}" via the live search filter ...')
    live_records = fetch_by_team_search(sample_team)
    live_by_year = {r['year']: r for r in live_records}

    stored_for_team = [r for r in records if r['team_name'] == sample_team]
    for stored in stored_for_team:
        live = live_by_year.get(stored['year'])
        if live is None:
            failures.append(f"{sample_team} {stored['year']}: not found in live re-fetch")
            continue
        if live['wins'] != stored['wins'] or live['losses'] != stored['losses']:
            failures.append(
                f"{sample_team} {stored['year']}: wins/losses mismatch — "
                f"stored=({stored['wins']}/{stored['losses']}) live=({live['wins']}/{live['losses']})"
            )
        else:
            print(f"✅ {sample_team} {stored['year']}: wins/losses match live source")

    return failures


def run_verification(data: list[dict]) -> bool:
    print('\n========== VERIFICATION ==========')

    dq_report = run_data_quality_report(
        data,
        required_fields=['team_name', 'wins', 'losses', 'win_pct'],  # ot_losses deliberately excluded — legitimately nullable
        numeric_fields=['wins', 'losses', 'goals_for', 'goals_against', 'win_pct'],
        key_fields=['team_name', 'year'],
        type_check_fields=['year', 'wins'],
    )
    print(dq_report['summary'])
    for f in dq_report['hard_failures']:
        print(f'   ❌ {f}')
    for w in dq_report['warnings']:
        print(f'   ⚠️  {w}')

    live_failures = check_against_live_source(data)

    all_failures = dq_report['hard_failures'] + live_failures
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
    data = load_local_data()
    print(f'Loaded {len(data)} records from p3_hockey_data.json')
    passed = run_verification(data)
    sys.exit(0 if passed else 1)
