"""
Project 3: Historical NHL team stats via a form-filterable, paginated
static HTML table.

Target: scrapethissite.com/pages/forms/ — the classic "forms" scraping
exercise. Server-rendered HTML (not JS), so plain httpx + BeautifulSoup
is enough — no browser automation needed.

Two query patterns are supported: a full crawl of every page, and a
filtered fetch using the site's own search form (?q=<team name>), which
is exactly how a real filter-driven UI (job boards, real estate sites,
e-commerce category pages) usually works under the hood.

Pagination technique: keep requesting page_num=1,2,3... until a page
returns zero rows. This is more robust than parsing the pager widget
itself, which shows a moving WINDOW of page numbers (e.g. "1..15" then
later "5..20") rather than the true last page.
"""
import time

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

BASE_URL = 'https://www.scrapethissite.com/pages/forms/'
REQUEST_DELAY = 0.4
MAX_PAGES_SAFETY = 100  # hard stop even if the "empty page" end signal somehow fails


class TeamSeasonStat(BaseModel):
    team_name: str = Field(min_length=1)
    year: int
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    ot_losses: int | None = None  # genuinely absent for seasons before 1999-2000 — not a bug
    win_pct: float = Field(ge=0, le=1)
    goals_for: int = Field(ge=0)
    goals_against: int = Field(ge=0)
    goal_diff: int  # can be negative — no ge=0 constraint


def _parse_optional_int(text: str) -> int | None:
    text = text.strip()
    return int(text) if text else None


def parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr', class_='team')
    records = []
    for row in rows:
        records.append({
            'team_name': row.find('td', class_='name').get_text(strip=True),
            'year': int(row.find('td', class_='year').get_text(strip=True)),
            'wins': int(row.find('td', class_='wins').get_text(strip=True)),
            'losses': int(row.find('td', class_='losses').get_text(strip=True)),
            'ot_losses': _parse_optional_int(row.find('td', class_='ot-losses').get_text()),
            'win_pct': float(row.find('td', class_='pct').get_text(strip=True)),
            'goals_for': int(row.find('td', class_='gf').get_text(strip=True)),
            'goals_against': int(row.find('td', class_='ga').get_text(strip=True)),
            'goal_diff': int(row.find('td', class_='diff').get_text(strip=True)),
        })
    return records


def fetch_pages(extra_params: dict | None = None) -> list[dict]:
    """Crawls every page (optionally filtered by extra_params, e.g. {'q': 'Boston'})
    until an empty page signals the end."""
    all_raw: list[dict] = []
    headers = {'User-Agent': 'portfolio-demo-scraper (contact: your-email)'}

    with httpx.Client(headers=headers, timeout=15) as client:
        for page_num in range(1, MAX_PAGES_SAFETY + 1):
            params = {'page_num': page_num}
            if extra_params:
                params.update(extra_params)

            resp = client.get(BASE_URL, params=params)
            resp.raise_for_status()
            page_records = parse_page(resp.text)

            if not page_records:
                print(f'   📄 Page {page_num}: 0 rows — reached the end.')
                break

            print(f'   📄 Page {page_num}: {len(page_records)} rows')
            all_raw.extend(page_records)
            time.sleep(REQUEST_DELAY)

    return all_raw


def fetch_all_teams() -> list[dict]:
    return fetch_pages()


def fetch_by_team_search(query: str) -> list[dict]:
    """Uses the site's own search form filter — same pattern as a real
    job-board/e-commerce category filter under the hood."""
    return fetch_pages({'q': query})


def validate(raw_records: list[dict]) -> list[dict]:
    validated = []
    for r in raw_records:
        try:
            validated.append(TeamSeasonStat(**r).model_dump())
        except Exception as e:
            print(f'⚠️ [Circuit Breaker] Skipped invalid record '
                  f'({r.get("team_name")}, {r.get("year")}): {e}')
    return validated


if __name__ == '__main__':
    # Standalone smoke test
    raw = fetch_all_teams()
    print(f'✅ Fetched {len(raw)} raw rows.')
    data = validate(raw)
    print(f'✅ Validated {len(data)} records.')
