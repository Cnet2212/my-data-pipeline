# Business Requirements — Project 2: Live Remote Job Listings Pipeline

## 1. Business Context
A recruiter or job-seeker-facing tool needs an always-current view of remote job openings without manually browsing multiple job boards. The goal is a single, searchable, exportable feed sourced from a legitimate public listings API.

## 2. Objective
Automatically pull current remote job postings, store them for reference, and present them in a dashboard that supports category/company filtering and keyword search.

## 3. Functional Requirements
| ID | Requirement |
|----|-------------|
| FR-1 | System shall retrieve up to 200 current remote job postings from Remotive |
| FR-2 | For each posting, capture: title, company, category, job type, location, salary (if listed), tags, publish date, and application URL |
| FR-3 | System shall reject and log any record missing a required field, without stopping the run |
| FR-4 | Records shall be stored in a queryable database, keyed so re-running the pipeline updates existing postings rather than duplicating them |
| FR-5 | Dashboard shall display total job count, category count, and company count |
| FR-6 | Dashboard shall support filtering by category and free-text search over job titles |
| FR-7 | Dashboard shall support exporting the currently filtered view as CSV |
| FR-8 | Dashboard shall link each listing to its original application page |

## 4. Non-Functional Requirements
| ID | Requirement |
|----|-------------|
| NFR-1 | A single fetch call is sufficient — no retry/concurrency complexity required for this data volume |
| NFR-2 | No cost — infrastructure must run on free tiers (Supabase free tier, Streamlit Community Cloud) |
| NFR-3 | All user-facing and log text in English |

## 5. Data Source
Remotive official public API (`remotive.com/api/remote-jobs`) — no authentication required.

## 6. Acceptance Criteria
- [ ] Running the fetcher once produces a local data file and (if configured) a populated Supabase table
- [ ] Running the fetcher a second time does not create duplicate rows for the same job posting
- [ ] Dashboard loads and displays data with no manual data-file editing required
- [ ] Category filter and title search visibly narrow the displayed table
- [ ] CSV export button produces a file matching the currently filtered rows
- [ ] `p2_jobs_verify.py` passes with no structural or cross-check failures

## 7. Out of Scope
- Salary normalization across currencies (raw salary string is stored as-is, since many postings omit it entirely)
- Deduplication of the same role cross-posted under slightly different titles
- Application tracking or submission — this is a discovery/browsing tool only

---

## Addendum — Escalated Requirements (Multi-Source, Data Quality, History, Caching)

### Additional Functional Requirements
| ID | Requirement |
|----|-------------|
| FR-9 | System shall aggregate postings from at least two independent job sources with different schemas |
| FR-10 | System shall normalize both sources into one unified record shape |
| FR-11 | System shall strip HTML markup from any free-text field before storage/display |
| FR-12 | System shall attempt to parse a numeric salary range where the source format allows, and store `null` (not a guess) where it cannot |
| FR-13 | System shall detect and remove duplicate postings for the same job appearing on multiple sources |
| FR-14 | System shall detect postings that appeared, changed, or disappeared since the previous run, and record each as a timestamped event |

### Additional Non-Functional Requirements
| ID | Requirement |
|----|-------------|
| NFR-4 | System shall not exceed any source's stated request quota (Remotive: max 4/day) — self-enforced client-side, since the source does not return an HTTP 429 |
| NFR-5 | Repeated runs within a source's data-freshness window shall not make redundant network calls |

### Additional Acceptance Criteria
- [x] Running the multi-source pipeline produces a single unified dataset from both sources
- [x] Duplicate cross-source postings are not double-counted (verified: 0 false-positive duplicates after fixing same-source comparison bug)
- [x] Re-running within the cache TTL makes no network calls (verified via log output)
- [x] A 5th same-day Remotive call is refused and falls back to cache instead of erroring
- [x] Editing/removing a posting in the cached source data is correctly reflected as "updated"/"removed" in the next diff (verified via manual cache-edit test)
- [x] Description fields contain no raw HTML markup — verified automatically by `p2_jobs_unified_verify.py` on every run (this required a real fix: the cleaning function existed but was not wired into the pipeline on first implementation — caught by asking "has this actually been verified?" before assuming done)
- [x] `python p2_jobs_multisource_pipeline.py` runs fetch through verification as a single command, exiting non-zero if verification fails

### Known Limitations (documented, not hidden)
- Salary parsing succeeds for a small minority of records (~1% in testing) — most real postings simply don't publish a machine-parseable salary, which is realistic, not a defect
- Cross-source fuzzy dedup found 0 actual matches in testing — expected, since Remotive (remote-only, global) and Arbeitnow (largely Germany-based, mixed remote/on-site) have limited audience overlap
