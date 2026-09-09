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


def save_jobs_to_db(jobs: list):
    supabase = get_supabase_client()
    try:
        # id is Remotive's own job id — real, stable unique key
        response = supabase.table('jobs').upsert(jobs, on_conflict='id').execute()
        return response
    except Exception as e:
        print(f'⚠️ DB connection warning: {e}')
        return None
