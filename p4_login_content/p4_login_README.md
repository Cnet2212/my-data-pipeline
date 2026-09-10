# Project 4 — Authenticated Crawl (CSRF Login + Session Cookies)

Logs in via a CSRF-protected form, maintains the session across a full paginated crawl, and verifies the login genuinely succeeded (not just that requests returned HTTP 200).

**Live dashboard:** _(add your Streamlit Cloud link here after deploying)_

## Stack
- **Auth mechanics:** `httpx.Client` (persists cookies automatically across requests) + `BeautifulSoup` to extract the CSRF token from the login form before submitting credentials
- **Login verification:** checks for the "Logout" link in the nav bar after posting credentials — a real assertion, not an assumption from status code alone
- **Pagination:** follows `li.next` links with the SAME authenticated client, so the session rides along
- **Data quality:** `shared_data_quality.py` (same module used since Project 3)
- **Validation:** Pydantic circuit-breaker pattern
- **Storage:** Supabase, upserted on the natural key `(author, text)`
- **Presentation:** Streamlit + `shared_dashboard_filters.py` — Excel-style multiselect on every column

## Important caveat about this target site
quotes.toscrape.com/login accepts ANY username/password and shows identical quote content whether logged in or not — it's a pure mechanics exercise (CSRF + session), not a real access-control demo. The verification step proves the LOGIN itself worked; it does not (and cannot, on this site) prove that login unlocks different data.

## Run it locally
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r p4_login_requirements.txt
python p4_login_pipeline.py    # login, fetch, validate, save, verify — one command
streamlit run p4_login_app.py
```
Copy `shared_data_quality.py` and `shared_dashboard_filters.py` into this folder before running. Run `p4_login_schema.sql` in the Supabase SQL editor once, before the first save.
