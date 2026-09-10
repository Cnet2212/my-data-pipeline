"""
Project 4: single-command pipeline — login, fetch, validate, save, verify.
"""
import json
import sys

from p4_login_fetcher import login_and_get_session, verify_logged_in, fetch_all_quotes, validate
from p4_login_verify import run_verification

if __name__ == '__main__':
    print('🔐 Logging in ...')
    client = login_and_get_session()
    if verify_logged_in(client):
        print('✅ Login confirmed (Logout link present).')
    else:
        print('⚠️  Login may not have succeeded — proceeding anyway since content is public regardless.')

    print('🔎 Fetching all pages ...')
    raw = fetch_all_quotes(client)
    print(f'✅ Fetched {len(raw)} raw quotes.')

    data = validate(raw)
    print(f'✅ Validated {len(data)} records.')

    try:
        from p4_login_db import save_quotes_to_db
        result = save_quotes_to_db(data)
        if result:
            print(f'☁️  Upserted {len(data)} records to Supabase.')
    except RuntimeError as e:
        print(f'ℹ️  Skipping Supabase save: {e}')

    with open('p4_login_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('💾 Saved p4_login_data.json')

    passed = run_verification(data)
    if not passed:
        print('\n❌ Pipeline completed but verification found issues — see above.')
        sys.exit(1)
