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


def save_stats_to_db(records: list):
    supabase = get_supabase_client()
    try:
        # A team plays exactly one season per year — (team_name, year) is
        # the natural real-world unique key, not an auto id.
        response = supabase.table('hockey_stats').upsert(records, on_conflict='team_name,year').execute()
        return response
    except Exception as e:
        print(f'⚠️ DB connection warning: {e}')
        return None
