# Project 1 — Live Content Aggregation Pipeline (Hacker News)

Fetches, validates, and stores the current top stories from Hacker News, then displays them on a live filterable dashboard.

**Live dashboard:** _(add your Streamlit Cloud link here after deploying)_

## Stack
- **Extraction:** `httpx` async client calling the official Hacker News public API directly (no browser automation needed — data is available as JSON)
- **Concurrency:** up to 10 simultaneous requests (semaphore-limited) to fetch 100 story details efficiently without hammering the API
- **Resilience:** per-request retry with exponential backoff (3 attempts)
- **Validation:** Pydantic schema with circuit-breaker pattern — invalid records are logged and skipped, never crash the run
- **Storage:** Supabase (PostgreSQL), upserted on Hacker News's own story `id` so re-running updates scores/comments instead of duplicating
- **Presentation:** Streamlit + Plotly, deployed on Streamlit Community Cloud

## What it does
`p1_hn_crawler.py` pulls the current top 100 story IDs from `hacker-news.firebaseio.com/v0/topstories.json`, fetches each story's detail concurrently, validates title/score/author/comment-count, and upserts into a `hn_stories` table. `p1_hn_app.py` reads that table and renders a dashboard: totals, average score/comments, a top-15-by-score chart, and a searchable/sortable table with links to each story.

## Run it locally
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r p1_hn_requirements.txt
python p1_hn_crawler.py      # fetches, validates, saves to p1_hn_data.json + Supabase
streamlit run p1_hn_app.py   # local dashboard at localhost:8501
```

Requires `SUPABASE_URL` and `SUPABASE_KEY` environment variables for the Supabase write/read steps; the dashboard falls back to the local `p1_hn_data.json` if those aren't set. Run `p1_hn_schema.sql` in the Supabase SQL editor once, before the first write.

## Notes
Data is real and live — re-running the crawler at any time reflects current Hacker News rankings, not a static snapshot.
