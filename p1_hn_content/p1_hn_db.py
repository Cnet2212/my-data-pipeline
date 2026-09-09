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


def save_stories_to_db(stories: list):
    # Let RuntimeError (missing env vars) bubble up to the caller, which prints
    # a friendly "skipping Supabase" info line instead of an alarming warning.
    supabase = get_supabase_client()
    try:
        # id is Hacker News's own story id — a real, stable unique key, so
        # re-running the crawler updates score/comment counts instead of duplicating.
        response = supabase.table('hn_stories').upsert(stories, on_conflict='id').execute()
        return response
    except Exception as e:
        print(f'⚠️ DB connection warning: {e}')
        return None
