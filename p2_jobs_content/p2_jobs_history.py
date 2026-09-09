"""
Historical tracking: compares this run's fetched dataset against the
previously stored state to detect new, removed, and updated postings,
and prepares both the upsert payload (current state, with status/
first_seen_at/last_seen_at) and an event log (append-only change history).

Without this, a plain upsert silently overwrites the previous snapshot —
you'd never know a job disappeared or its salary changed between runs.
"""
from datetime import datetime, timezone

# Fields that count as "the posting changed" if they differ between runs.
# Tags are compared separately as a set (order shouldn't matter).
TRACKED_FIELDS = ('title', 'company', 'location', 'remote', 'salary_min', 'salary_max', 'url')

# Only these fields are ever written back to the DB. Defensive allowlist —
# if fetch_existing_unified_jobs() ever returns extra columns (e.g. row_id,
# or a future column added by another surface), they get dropped here
# instead of silently breaking the next upsert.
UPSERT_FIELDS = (
    'source', 'source_id', 'title', 'company', 'location', 'remote', 'tags',
    'salary_raw', 'salary_min', 'salary_max', 'url', 'posted_at',
    'first_seen_at', 'last_seen_at', 'status',
)


def _clean(record: dict) -> dict:
    return {k: v for k, v in record.items() if k in UPSERT_FIELDS}


def _tags_set(record: dict) -> set:
    return set(record.get('tags') or [])


def _record_changed(old: dict, new: dict) -> bool:
    for field in TRACKED_FIELDS:
        if old.get(field) != new.get(field):
            return True
    return _tags_set(old) != _tags_set(new)


def compute_history(current_records: list[dict], existing_records: list[dict]) -> dict:
    """
    current_records: this run's freshly fetched + normalized + deduped data
    existing_records: what was already in the DB from the previous run
                       (each must include source, source_id, status, first_seen_at)

    Returns a dict with:
      - upsert_payload: current_records enriched with status/first_seen_at/last_seen_at,
                         PLUS records for anything newly detected as removed
      - events: list of {source, source_id, event_type, detected_at} for new/updated/removed
      - summary: counts for a human-readable report
    """
    existing_by_key = {(r['source'], r['source_id']): r for r in existing_records}
    current_by_key = {(r['source'], r['source_id']): r for r in current_records}
    now_iso = datetime.now(timezone.utc).isoformat()

    new_keys, updated_keys, unchanged_keys = [], [], []
    upsert_payload = []

    for key, record in current_by_key.items():
        existing = existing_by_key.get(key)
        enriched = dict(record)

        if existing is None:
            new_keys.append(key)
            enriched['first_seen_at'] = now_iso
        else:
            enriched['first_seen_at'] = existing.get('first_seen_at') or now_iso
            if existing.get('status') != 'active' or _record_changed(existing, record):
                updated_keys.append(key)  # includes "reappeared after being removed"
            else:
                unchanged_keys.append(key)

        enriched['status'] = 'active'
        enriched['last_seen_at'] = now_iso
        upsert_payload.append(_clean(enriched))

    removed_keys = [
        key for key, existing in existing_by_key.items()
        if key not in current_by_key and existing.get('status') == 'active'
    ]
    for key in removed_keys:
        removed_record = dict(existing_by_key[key])
        removed_record['status'] = 'removed'
        # last_seen_at intentionally NOT updated — it should reflect the
        # last time this posting was actually seen, not this run.
        upsert_payload.append(_clean(removed_record))

    events = []
    for key in new_keys:
        events.append({'source': key[0], 'source_id': key[1], 'event_type': 'new', 'detected_at': now_iso})
    for key in updated_keys:
        events.append({'source': key[0], 'source_id': key[1], 'event_type': 'updated', 'detected_at': now_iso})
    for key in removed_keys:
        events.append({'source': key[0], 'source_id': key[1], 'event_type': 'removed', 'detected_at': now_iso})

    summary = {
        'new': len(new_keys),
        'updated': len(updated_keys),
        'removed': len(removed_keys),
        'unchanged': len(unchanged_keys),
    }
    return {'upsert_payload': upsert_payload, 'events': events, 'summary': summary}
