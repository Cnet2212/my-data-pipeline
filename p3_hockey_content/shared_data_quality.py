"""
Shared data-quality profiling module — reused identically across every
project in this repo (copy this exact file into each project folder).

Unlike Pydantic validation (which checks each record's SHAPE against a
schema and is already used in every project), this module looks for
issues that a schema alone can't catch: encoding artifacts, leftover
HTML, inconsistent types across the SAME field, malformed URLs,
duplicate keys, numeric outliers, and messy whitespace. These are the
kinds of problems real scraped/API data actually has, independent of
whether the data technically "validates".

Usage pattern in a project's own verify script:

    from shared_data_quality import run_data_quality_report

    report = run_data_quality_report(
        records,
        required_fields=['title', 'url'],
        url_fields=['url'],
        text_fields=['title', 'description'],
        numeric_fields=['price', 'score'],
        key_fields=['id'],
    )
    print(report['summary'])
    if report['hard_failures']:
        ...  # treat as real problems
    if report['warnings']:
        ...  # informational, worth a human glance but not necessarily a defect
"""
import re
import statistics
from urllib.parse import urlparse

HTML_TAG_RE = re.compile(r'<[a-zA-Z/][^>]*>')
# Common mojibake byte-sequences from double-encoded UTF-8 (e.g. "café" -> "cafÃ©")
MOJIBAKE_RE = re.compile(r'Ã.|â€.|�')
WHITESPACE_ISSUE_RE = re.compile(r'^\s|\s$|\s{2,}')


def check_missing_required_fields(records: list[dict], required_fields: list[str]) -> list[str]:
    failures = []
    for field in required_fields:
        empty = [r for r in records if not str(r.get(field, '')).strip()]
        if empty:
            failures.append(f'{len(empty)}/{len(records)} records have empty/missing "{field}"')
    return failures


def check_duplicate_keys(records: list[dict], key_fields: list[str]) -> list[str]:
    failures = []
    keys = [tuple(r.get(f) for f in key_fields) for r in records]
    if len(keys) != len(set(keys)):
        dupes = len(keys) - len(set(keys))
        failures.append(f'{dupes} duplicate record(s) on key {tuple(key_fields)}')
    return failures


def check_malformed_urls(records: list[dict], url_fields: list[str]) -> list[str]:
    failures = []
    for field in url_fields:
        bad = []
        for r in records:
            val = r.get(field)
            if not val:
                continue  # empty is caught by check_missing_required_fields if it's required
            parsed = urlparse(val)
            if parsed.scheme not in ('http', 'https') or not parsed.netloc:
                bad.append(val)
        if bad:
            failures.append(f'{len(bad)} malformed "{field}" value(s), e.g. {bad[0]!r}')
    return failures


def check_type_consistency(records: list[dict], fields: list[str]) -> list[str]:
    """Flags a field that has more than one Python type across records —
    a common symptom of an API/site changing its response shape mid-stream,
    or a normalization bug that only handles one source's format."""
    failures = []
    for field in fields:
        types_seen = {type(r[field]).__name__ for r in records if field in r and r[field] is not None}
        if len(types_seen) > 1:
            failures.append(f'"{field}" has inconsistent types across records: {sorted(types_seen)}')
    return failures


def check_html_residue(records: list[dict], text_fields: list[str]) -> list[str]:
    failures = []
    for field in text_fields:
        bad = [r for r in records if HTML_TAG_RE.search(str(r.get(field) or ''))]
        if bad:
            failures.append(f'{len(bad)} record(s) still contain raw HTML tags in "{field}"')
    return failures


def check_encoding_artifacts(records: list[dict], text_fields: list[str]) -> list[str]:
    """Flags likely mojibake (text that was decoded with the wrong
    encoding at some point) — this doesn't crash anything, it just quietly
    corrupts non-ASCII text, which is easy to miss without an explicit check."""
    warnings = []
    for field in text_fields:
        bad = [r for r in records if MOJIBAKE_RE.search(str(r.get(field) or ''))]
        if bad:
            warnings.append(f'{len(bad)} record(s) show likely encoding artifacts in "{field}" (e.g. mojibake)')
    return warnings


def check_whitespace_issues(records: list[dict], text_fields: list[str]) -> list[str]:
    warnings = []
    for field in text_fields:
        bad = [r for r in records if WHITESPACE_ISSUE_RE.search(str(r.get(field) or ''))]
        if bad:
            warnings.append(f'{len(bad)} record(s) have leading/trailing/double whitespace in "{field}"')
    return warnings


def check_numeric_outliers(records: list[dict], numeric_fields: list[str]) -> list[str]:
    """IQR-based outlier flagging — informational, NOT a hard failure.
    A real outlier (a $500,000 salary in a dataset of $50k jobs) might be
    completely legitimate; this just surfaces it for a human to glance at."""
    warnings = []
    for field in numeric_fields:
        values = sorted(r[field] for r in records if isinstance(r.get(field), (int, float)))
        if len(values) < 8:
            continue  # not enough data for a meaningful IQR
        q1 = statistics.quantiles(values, n=4)[0]
        q3 = statistics.quantiles(values, n=4)[2]
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = [v for v in values if v < low or v > high]
        if outliers:
            warnings.append(
                f'{len(outliers)} outlier value(s) in "{field}" outside [{low:.1f}, {high:.1f}] '
                f'(e.g. {outliers[0]})'
            )
    return warnings


def run_data_quality_report(
    records: list[dict],
    required_fields: list[str] | None = None,
    url_fields: list[str] | None = None,
    text_fields: list[str] | None = None,
    numeric_fields: list[str] | None = None,
    key_fields: list[str] | None = None,
    type_check_fields: list[str] | None = None,
) -> dict:
    """Runs every applicable check and separates results into hard_failures
    (real defects — missing data, duplicates, malformed structure) and
    warnings (informational — outliers, encoding, whitespace; worth a look
    but not necessarily wrong)."""
    hard_failures: list[str] = []
    warnings: list[str] = []

    if required_fields:
        hard_failures += check_missing_required_fields(records, required_fields)
    if key_fields:
        hard_failures += check_duplicate_keys(records, key_fields)
    if url_fields:
        hard_failures += check_malformed_urls(records, url_fields)
    if type_check_fields:
        hard_failures += check_type_consistency(records, type_check_fields)
    if text_fields:
        hard_failures += check_html_residue(records, text_fields)
        warnings += check_encoding_artifacts(records, text_fields)
        warnings += check_whitespace_issues(records, text_fields)
    if numeric_fields:
        warnings += check_numeric_outliers(records, numeric_fields)

    summary = (
        f'{len(records)} records checked — {len(hard_failures)} hard failure(s), '
        f'{len(warnings)} warning(s)'
    )
    return {'hard_failures': hard_failures, 'warnings': warnings, 'summary': summary}
