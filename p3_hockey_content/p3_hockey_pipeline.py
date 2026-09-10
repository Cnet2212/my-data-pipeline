"""
Project 3: single-command pipeline — fetch, validate, save, verify.
"""
import json
import sys

from p3_hockey_fetcher import fetch_all_teams, validate
from p3_hockey_verify import run_verification

if __name__ == '__main__':
    print('🔎 Fetching all pages ...')
    raw = fetch_all_teams()
    print(f'✅ Fetched {len(raw)} raw rows across all pages.')

    data = validate(raw)
    print(f'✅ Validated {len(data)} records.')

    try:
        from p3_hockey_db import save_stats_to_db
        result = save_stats_to_db(data)
        if result:
            print(f'☁️  Upserted {len(data)} records to Supabase.')
    except RuntimeError as e:
        print(f'ℹ️  Skipping Supabase save: {e}')

    with open('p3_hockey_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('💾 Saved p3_hockey_data.json')

    passed = run_verification(data)
    if not passed:
        print('\n❌ Pipeline completed but verification found issues — see above.')
        sys.exit(1)
