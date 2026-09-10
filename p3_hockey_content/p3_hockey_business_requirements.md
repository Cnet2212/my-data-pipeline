# Business Requirements — Project 3: Historical NHL Team Stats

## 1. Business Context
An analyst wants a complete historical dataset of NHL team performance by season, sourced from a public stats page that only exposes data through a paginated, filterable form UI — not a bulk export.

## 2. Objective
Crawl every page of team-season records, validate the data (accounting for a stat that genuinely doesn't exist in older records), and present it as a browsable, filterable historical dashboard.

## 3. Functional Requirements
| ID | Requirement |
|----|-------------|
| FR-1 | System shall crawl every page of results, not just the first page |
| FR-2 | System shall support fetching a filtered subset via the site's own search parameter |
| FR-3 | System shall capture: team name, year, wins, losses, OT losses (if present), win %, goals for/against, goal differential |
| FR-4 | System shall NOT reject a record solely for missing OT losses on pre-2000 seasons |
| FR-5 | System shall reject and log any record with a genuinely invalid required field |
| FR-6 | Records shall be stored keyed by (team, year) so re-running updates rather than duplicates |
| FR-7 | Dashboard shall support filtering by team and by year range |
| FR-8 | Dashboard shall chart win % over time |

## 4. Non-Functional Requirements
| ID | Requirement |
|----|-------------|
| NFR-1 | Pagination shall not assume a fixed total page count — must detect the actual end of data |
| NFR-2 | A single run shall run data-quality checks automatically, not as a separate manual step |
| NFR-3 | No cost — free tiers only |

## 5. Data Source
scrapethissite.com/pages/forms/ — a public scraping-practice site (server-rendered HTML, form-based filter, numbered pagination).

## 6. Acceptance Criteria
- [ ] `python p3_hockey_pipeline.py` fetches all pages, validates, saves, and verifies in one command
- [ ] Pre-2000 seasons with no OT-losses value are NOT flagged as data-quality failures
- [ ] Re-running the pipeline does not duplicate team-season rows
- [ ] `shared_data_quality.py` catches at least one class of real issue if deliberately introduced (verify by editing a cached/local response, as done in Project 2)
- [ ] Dashboard's win % chart renders correctly for both a single selected team and the "All" view

## 7. Out of Scope
- Player-level or game-level statistics (this source only provides team-season aggregates)
- Multi-source cross-referencing (per the earlier scoping discussion, this project intentionally stays single-source — forcing a second source here would be artificial complexity)
