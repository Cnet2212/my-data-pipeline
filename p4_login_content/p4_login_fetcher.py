"""
Project 4: authenticated crawl via CSRF-token login + session cookies.

Target: quotes.toscrape.com/login — the classic session-handling exercise.
Any username/password combination is accepted (this is a practice site);
the point is the MECHANICS: extract the CSRF token from the login form,
submit it alongside credentials, and reuse the resulting session cookie
for subsequent requests — exactly what's needed for any real site with a
login wall, even though this particular site shows identical content
whether logged in or not.
"""
import time

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

BASE_URL = 'https://quotes.toscrape.com'
LOGIN_URL = f'{BASE_URL}/login'
MAX_RETRIES = 3
BACKOFF_BASE = 1.5
REQUEST_DELAY = 0.4


class Quote(BaseModel):
    text: str = Field(min_length=1)
    author: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


def login_and_get_session(username: str = 'practice', password: str = 'practice') -> httpx.Client:
    """Returns an authenticated httpx.Client whose cookie jar carries the
    session forward into every subsequent request made with it."""
    client = httpx.Client(
        headers={'User-Agent': 'portfolio-demo-scraper (contact: your-email)'},
        follow_redirects=True,
        timeout=15,
    )

    login_page = client.get(LOGIN_URL)
    soup = BeautifulSoup(login_page.text, 'html.parser')
    csrf_input = soup.find('input', {'name': 'csrf_token'})
    if csrf_input is None:
        raise RuntimeError('Could not find csrf_token field on the login page — page structure may have changed.')
    csrf_token = csrf_input.get('value')

    client.post(LOGIN_URL, data={
        'csrf_token': csrf_token,
        'username': username,
        'password': password,
    })
    return client


def verify_logged_in(client: httpx.Client) -> bool:
    """The nav bar shows 'Logout' only when a valid session cookie is
    present — the most direct proof the login actually worked, rather
    than just assuming a 200 status means success."""
    resp = client.get(BASE_URL)
    return 'Logout' in resp.text


def _get_with_retry(client: httpx.Client, url: str) -> httpx.Response:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return client.get(url)
        except Exception as e:
            last_error = e
            if attempt == MAX_RETRIES:
                break
            time.sleep(BACKOFF_BASE ** attempt)
    raise RuntimeError(f'Could not load {url} after {MAX_RETRIES} attempts: {last_error}')


def parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, 'html.parser')
    records = []
    for quote_div in soup.find_all('div', class_='quote'):
        records.append({
            'text': quote_div.find('span', class_='text').get_text(strip=True),
            'author': quote_div.find('small', class_='author').get_text(strip=True),
            'tags': [a.get_text(strip=True) for a in quote_div.find_all('a', class_='tag')],
        })
    return records


def fetch_all_quotes(client: httpx.Client) -> list[dict]:
    """Crawls every page using the SAME authenticated client, so the
    session cookie rides along with each request — this is the part that
    would matter on a real login-gated site."""
    all_raw: list[dict] = []
    url = BASE_URL + '/'

    while url:
        resp = _get_with_retry(client, url)
        page_records = parse_page(resp.text)
        print(f'   📄 {url}: {len(page_records)} quotes')
        all_raw.extend(page_records)

        soup = BeautifulSoup(resp.text, 'html.parser')
        next_li = soup.find('li', class_='next')
        if next_li:
            url = BASE_URL + next_li.find('a')['href']
            time.sleep(REQUEST_DELAY)
        else:
            url = None

    return all_raw


def validate(raw_records: list[dict]) -> list[dict]:
    validated = []
    for r in raw_records:
        try:
            validated.append(Quote(**r).model_dump())
        except Exception as e:
            print(f'⚠️ [Circuit Breaker] Skipped invalid record: {e}')
    return validated


if __name__ == '__main__':
    client = login_and_get_session()
    print(f'🔐 Login successful: {verify_logged_in(client)}')
    raw = fetch_all_quotes(client)
    print(f'✅ Fetched {len(raw)} raw quotes.')
    data = validate(raw)
    print(f'✅ Validated {len(data)} records.')
