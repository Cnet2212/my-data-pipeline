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


def fetch_existing_unified_jobs() -> list[dict]:
    """Reads current state from the DB so this run can be diffed against
    it. Selects specific columns (not '*') to exclude row_id — an
    auto-generated identity column that Postgres refuses to receive back
    as an explicit value on upsert. Returns [] if the table is empty
    (e.g. first-ever run) — the history module treats that correctly as
    "everything is new"."""
    supabase = get_supabase_client()
    columns = (
        'source, source_id, title, company, location, remote, tags, '
        'salary_raw, salary_min, salary_max, url, posted_at, '
        'first_seen_at, last_seen_at, status'
    )
    response = supabase.table('jobs_unified').select(columns).execute()
    return response.data or []


def save_unified_jobs_to_db(records: list):
    supabase = get_supabase_client()
    try:
        # source_id alone isn't globally unique (a Remotive int id could in
        # principle collide with an Arbeitnow slug) — the real unique key
        # is the (source, source_id) pair, so both columns go in on_conflict.
        response = supabase.table('jobs_unified').upsert(records, on_conflict='source,source_id').execute()
        return response
    except Exception as e:
        print(f'⚠️ DB connection warning: {e}')
        return None


def save_events_to_db(events: list):
    if not events:
        return None
    supabase = get_supabase_client()
    try:
        # Events are an append-only log, not upserted — each detected
        # change is its own row, never overwritten.
        response = supabase.table('jobs_unified_events').insert(events).execute()
        return response
    except Exception as e:
        print(f'⚠️ DB connection warning (events): {e}')
        return None
