"""
Project 2 (escalated): multi-source job aggregation pipeline with
historical tracking.

Pulls from two independent job APIs (Remotive + Arbeitnow), normalizes
schemas, fuzzy-dedupes across sources, then diffs the result against
previously stored state to detect new/updated/removed postings — and
logs each change as an event, so the pipeline builds a real history
instead of silently overwriting the previous snapshot on every run.
"""
import json
import sys

from p2_jobs_fetcher import fetch_jobs as fetch_remotive_jobs
from p2_jobs_arbeitnow_fetcher import fetch_arbeitnow_jobs
from p2_jobs_normalize import build_unified_dataset
from p2_jobs_history import compute_history
from p2_jobs_unified_verify import run_verification

if __name__ == '__main__':
    print('🔎 Fetching Remotive ...')
    remotive_jobs = fetch_remotive_jobs()
    print(f'   -> {len(remotive_jobs)} Remotive jobs')

    print('🔎 Fetching Arbeitnow ...')
    arbeitnow_jobs = fetch_arbeitnow_jobs()
    print(f'   -> {len(arbeitnow_jobs)} Arbeitnow jobs')

    data, errors = build_unified_dataset(remotive_jobs, arbeitnow_jobs)
    for err in errors:
        print(f'⚠️ {err}')
    print(f'✅ Unified dataset: {len(data)} validated records.')

    salary_parsed = sum(1 for r in data if r['salary_min'] is not None)
    print(f'   ℹ️  Salary successfully parsed for {salary_parsed}/{len(data)} records '
          f'({salary_parsed / len(data) * 100:.0f}%) — the rest had no salary field or an unparseable format.')

    try:
        from p2_jobs_unified_db import fetch_existing_unified_jobs, save_unified_jobs_to_db, save_events_to_db

        existing = fetch_existing_unified_jobs()
        history = compute_history(data, existing)

        s = history['summary']
        print(f"📊 History diff vs previous run: {s['new']} new, {s['updated']} updated, "
              f"{s['removed']} removed, {s['unchanged']} unchanged.")

        result = save_unified_jobs_to_db(history['upsert_payload'])
        if result:
            print(f"☁️  Upserted {len(history['upsert_payload'])} records to Supabase (jobs_unified).")

        events_result = save_events_to_db(history['events'])
        if events_result:
            print(f"☁️  Logged {len(history['events'])} change event(s) to jobs_unified_events.")
        elif history['events']:
            print('ℹ️  No events logged (DB save may have failed above — see warning if any).')

    except RuntimeError as e:
        print(f'ℹ️  Skipping Supabase save (and history tracking, which requires it): {e}')

    with open('p2_jobs_unified_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('💾 Saved p2_jobs_unified_data.json')

    passed = run_verification(data)
    if not passed:
        print('\n❌ Pipeline completed but verification found issues — see above. Exiting with error status.')
        sys.exit(1)
