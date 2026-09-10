import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')


def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            'SUPABASE_URL / SUPABASE_KEY environment variables are not set.'
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def save_quotes_to_db(records: list):
    supabase = get_supabase_client()
    try:
        # (author, text) is the natural unique key — this is a fixed,
        # curated set of quotes on the practice site, not a growing feed.
        response = supabase.table('quotes').upsert(records, on_conflict='author,text').execute()
        return response
    except Exception as e:
        print(f'⚠️ DB connection warning: {e}')
        return None
