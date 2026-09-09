# Project 2 — Multi-Source Job Aggregation Pipeline (with history tracking)

Fetches remote/on-site job postings from two independent real APIs, normalizes their different schemas into one, deduplicates across sources, caches to respect stated API quotas, and tracks new/updated/removed postings over time.

**Live dashboard:** _(add your Streamlit Cloud link here after deploying)_

## Architecture
```
p2_jobs_fetcher.py ─────────┐
  (Remotive, quota-limited)  │
                              ├─► p2_jobs_normalize.py ─► p2_jobs_history.py ─► Supabase
p2_jobs_arbeitnow_fetcher.py─┘    (schema unify, HTML       (diff vs previous    (jobs_unified +
  (Arbeitnow, paginated)          clean, salary parse,       state, event log)    jobs_unified_events)
                                   fuzzy cross-source
                                   dedupe, exact-id dedupe)
```
Both fetchers go through `p2_jobs_cache.py` first — a local TTL cache plus a rolling-window quota tracker, so repeated runs within the cache window make zero network calls.

## Stack
- **Extraction:** `httpx`, two independent public APIs (Remotive — capped free tier, 18 postings; Arbeitnow — paginated, ~600 postings across 3 pages)
- **Caching/quota:** file-based TTL cache (`.p2_cache/`) + rolling 24h call counter, enforcing Remotive's stated "max 4 requests/day" even though the API itself doesn't return an HTTP 429
- **Normalization:** unified `UnifiedJob` schema across both sources' very different field names/types
- **Data quality:** HTML-tag stripping + entity unescaping on descriptions, best-effort salary range parsing (returns `None` rather than guessing on ambiguous formats)
- **Deduplication:** two layers — fuzzy title+company similarity across sources (`difflib`), and exact `(source, source_id)` dedup to handle pagination overlap on a live-updating source
- **History tracking:** each run diffs against the DB's current state to detect new/updated/removed postings, updates `status`/`first_seen_at`/`last_seen_at`, and appends to an immutable `jobs_unified_events` log
- **Validation:** Pydantic circuit-breaker pattern, as in all four projects
- **Presentation:** Streamlit + Plotly

## Run it locally
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r p2_jobs_requirements.txt
python p2_jobs_multisource_pipeline.py   # fetches (or uses cache), normalizes, dedupes, diffs history, saves
streamlit run p2_jobs_app.py             # local dashboard at localhost:8501
```

Run `p2_jobs_schema.sql`, then `p2_jobs_unified_schema.sql`, then `p2_jobs_history_schema.sql` (in that order) in the Supabase SQL editor before the first run. Requires `SUPABASE_URL` / `SUPABASE_KEY` environment variables — without them the pipeline still runs and saves locally, but history tracking is skipped (it requires reading previous state from the DB).

## Attribution requirement
Per Remotive's API terms, any display of their data must link back to remotive.com — already included in `p2_jobs_app.py`.

## Verifying output accuracy
`p2_jobs_verify.py` checks the single-source Remotive fetch against a fresh live call. (A multi-source equivalent for the unified pipeline is a natural next addition.)
