# Project 3 — Historical NHL Team Stats (Form Filter + Full Pagination)

Crawls every page of a server-rendered, form-filterable stats table, validates it (including a genuinely optional field), and stores it for a historical dashboard.

**Live dashboard:** _(add your Streamlit Cloud link here after deploying)_

## Stack
- **Extraction:** `httpx` + `BeautifulSoup` (server-rendered static HTML — no browser automation needed)
- **Pagination:** increments `?page_num=` until a page returns zero rows, rather than parsing the pager widget's moving window of visible page numbers
- **Form filtering:** reuses the site's own `?q=<team>` search parameter — the same mechanic a real filtered job/product listing uses under the hood
- **Data quality:** shared `shared_data_quality.py` module (same file used across every project from this point on) — checks for missing fields, duplicate keys, type inconsistency, numeric outliers
- **Validation:** Pydantic, with `ot_losses` deliberately nullable — this stat genuinely doesn't exist for NHL seasons before 1999-2000, so treating it as "missing" would be a false alarm
- **Storage:** Supabase, upserted on the real-world natural key `(team_name, year)`
- **Presentation:** Streamlit + Plotly — win% trend line, filterable by team and year range

## Run it locally
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r p3_hockey_requirements.txt
python p3_hockey_pipeline.py    # fetch, validate, save, verify — all in one command
streamlit run p3_hockey_app.py
```
Copy `shared_data_quality.py` into this folder before running (same file as used in later projects). Run `p3_hockey_schema.sql` in the Supabase SQL editor once, before the first save.
