"""
Schema normalization layer for multi-source job aggregation.

This is the core "real world" skill in this project: two legitimate APIs
describe the same kind of thing (a job posting) with completely different
field names, types, and completeness — this module maps both into one
UnifiedJob schema, cleans text, parses what data quality it can out of
inconsistent fields, and de-duplicates the same job appearing on both boards.
"""
import html
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

from pydantic import BaseModel, Field

HTML_TAG_RE = re.compile(r'<[^>]+>')
SALARY_NUMBER_RE = re.compile(r'[\d,]+(?:\.\d+)?')

DEDUPE_SIMILARITY_THRESHOLD = 0.90  # how close title+company must be to count as "the same job"


class UnifiedJob(BaseModel):
    source: str
    source_id: str
    title: str = Field(min_length=1)
    company: str
    location: str = 'Unknown'
    remote: bool = False
    tags: list[str] = Field(default_factory=list)
    salary_raw: str = ''
    salary_min: float | None = None
    salary_max: float | None = None
    url: str
    posted_at: str


def clean_html(raw: str) -> str:
    """Strip HTML tags and unescape entities — Arbeitnow's description
    field arrives as raw HTML (<p>, <ul>, &#x26; for &, etc.)."""
    if not raw:
        return ''
    text = HTML_TAG_RE.sub(' ', raw)
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def parse_salary(raw: str) -> tuple[float | None, float | None]:
    """Best-effort extraction of a numeric min/max from free-text salary
    strings like '$50,000 - $70,000', '50k-70k', 'Negotiable', or ''.
    Real salary fields are messy enough that a fully general parser isn't
    realistic — this handles the common cases and gives up gracefully
    (returns None, None) rather than guessing on ambiguous input."""
    if not raw:
        return None, None

    text = raw.lower().replace(',', '')
    numbers = SALARY_NUMBER_RE.findall(text)
    if not numbers:
        return None, None

    values = []
    for n in numbers:
        val = float(n)
        # Handle "50k" / "70k" shorthand
        if 'k' in text[text.find(n) + len(n): text.find(n) + len(n) + 2]:
            val *= 1000
        values.append(val)

    if len(values) == 1:
        return values[0], values[0]
    return min(values), max(values)


def normalize_remotive(job: dict) -> dict:
    salary_min, salary_max = parse_salary(job.get('salary', ''))
    return {
        'source': 'remotive',
        'source_id': str(job['id']),
        'title': job.get('title', ''),
        'company': job.get('company', 'Unknown'),
        'location': job.get('location', 'Unknown'),
        'remote': True,  # Remotive is a remote-only job board by definition
        'tags': list(set((job.get('tags') or []) + [job.get('category', '')])),
        'salary_raw': job.get('salary', '') or '',
        'salary_min': salary_min,
        'salary_max': salary_max,
        'url': job.get('url', ''),
        'posted_at': job.get('published_at', ''),
    }


def normalize_arbeitnow(job: dict) -> dict:
    created_at = job.get('created_at')
    posted_at = (
        datetime.fromtimestamp(created_at, tz=timezone.utc).isoformat()
        if isinstance(created_at, (int, float)) else ''
    )
    return {
        'source': 'arbeitnow',
        'source_id': job.get('slug', ''),
        'title': job.get('title', ''),
        'company': job.get('company_name', 'Unknown'),
        'location': job.get('location', 'Unknown'),
        'remote': bool(job.get('remote', False)),
        'tags': list(set((job.get('tags') or []) + (job.get('job_types') or []))),
        'salary_raw': '',       # Arbeitnow does not provide a salary field at all
        'salary_min': None,
        'salary_max': None,
        'url': job.get('url', ''),
        'posted_at': posted_at,
    }


def _dedupe_key(record: dict) -> str:
    return f"{record['title'].strip().lower()}|{record['company'].strip().lower()}"


def fuzzy_dedupe(records: list[dict]) -> tuple[list[dict], int]:
    """Cross-source duplicate detection: the same posting often appears on
    multiple boards with near-identical (not always exact) title/company
    text. Exact-match on source_id can't catch this since ids are
    source-specific — this compares normalized title+company similarity.
    Between two matches, keeps the one with more complete data (has a
    parsed salary, or a longer tag list)."""
    kept: list[dict] = []
    removed = 0

    for record in records:
        key = _dedupe_key(record)
        match_idx = None
        for i, existing in enumerate(kept):
            # Only compare across DIFFERENT sources — two distinct Arbeitnow
            # postings that happen to share a similar title (common with
            # generic titles like "Software Engineer") are not duplicates,
            # and must never be merged away.
            if existing['source'] == record['source']:
                continue
            existing_key = _dedupe_key(existing)
            similarity = SequenceMatcher(None, key, existing_key).ratio()
            if similarity >= DEDUPE_SIMILARITY_THRESHOLD:
                match_idx = i
                break

        if match_idx is None:
            kept.append(record)
            continue

        removed += 1
        existing = kept[match_idx]
        existing_score = (existing['salary_min'] is not None) + len(existing['tags'])
        new_score = (record['salary_min'] is not None) + len(record['tags'])
        if new_score > existing_score:
            kept[match_idx] = record  # the new record has more complete data — keep it instead

    return kept, removed


def build_unified_dataset(remotive_jobs: list[dict], arbeitnow_raw_jobs: list[dict]) -> tuple[list[dict], list[str]]:
    normalized = [normalize_remotive(j) for j in remotive_jobs]
    normalized += [normalize_arbeitnow(j) for j in arbeitnow_raw_jobs]

    deduped, removed_count = fuzzy_dedupe(normalized)
    max_possible_cross_source_dupes = min(len(remotive_jobs), len(arbeitnow_raw_jobs))
    if removed_count > max_possible_cross_source_dupes:
        print(f'⚠️ Sanity check failed: removed {removed_count} "duplicates" but the smaller '
              f'source only has {max_possible_cross_source_dupes} records — this points to a bug '
              f'in dedupe logic, not real cross-source duplicates. Investigate before trusting this run.')
    print(f'🔗 Deduplication: {len(normalized)} normalized records -> {len(deduped)} unique ({removed_count} cross-source duplicates removed)')

    # Hard dedupe on the exact (source, source_id) key — offset-based pagination
    # against a live-updating source (Arbeitnow refreshes hourly) can return the
    # same job twice across page boundaries if new postings shift the list mid-fetch.
    # A DB unique constraint would reject the whole batch if this isn't caught first.
    exact_seen: dict[tuple[str, str], dict] = {}
    exact_dupe_count = 0
    for record in deduped:
        key = (record['source'], record['source_id'])
        if key in exact_seen:
            exact_dupe_count += 1
        exact_seen[key] = record  # last occurrence wins (freshest fetch)
    if exact_dupe_count:
        print(f'🔗 Exact-id dedupe: removed {exact_dupe_count} same-source pagination overlap duplicate(s)')
    deduped = list(exact_seen.values())

    validated = []
    errors = []
    for record in deduped:
        try:
            validated.append(UnifiedJob(**record).model_dump())
        except Exception as e:
            errors.append(f"[Circuit Breaker] Skipped invalid record (source={record.get('source')}, id={record.get('source_id')}): {e}")

    return validated, errors
