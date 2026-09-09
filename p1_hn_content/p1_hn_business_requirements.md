# Business Requirements — Project 1: Live Content Aggregation Pipeline

## 1. Business Context
A content team needs a way to monitor what's currently trending in the tech/startup discussion space (Hacker News) without manually refreshing the site. The goal is a lightweight, always-current feed that can be checked at a glance and exported for further use (e.g. picking topics for a newsletter or social content calendar).

## 2. Objective
Automatically pull the current top-ranked stories, store them for historical reference, and present them in a dashboard that supports quick filtering and search — refreshed on demand by re-running the pipeline.

## 3. Functional Requirements
| ID | Requirement |
|----|-------------|
| FR-1 | System shall retrieve the current top N stories (default: 100) from Hacker News |
| FR-2 | For each story, capture: title, source URL, score, author, comment count, and publish time |
| FR-3 | System shall reject and log any record missing a required field, without stopping the run |
| FR-4 | Records shall be stored in a queryable database, keyed so re-running the pipeline updates existing records rather than duplicating them |
| FR-5 | Dashboard shall display total story count, average score, and average comment count |
| FR-6 | Dashboard shall support free-text search over story titles |
| FR-7 | Dashboard shall support exporting the currently filtered view as CSV |
| FR-8 | Dashboard shall link each story to its original source |

## 4. Non-Functional Requirements
| ID | Requirement |
|----|-------------|
| NFR-1 | Fetching 100 stories should complete in well under a minute (concurrency required) |
| NFR-2 | A single failed request must not abort the entire run (retry + graceful skip required) |
| NFR-3 | No cost — infrastructure must run on free tiers (Supabase free tier, Streamlit Community Cloud) |
| NFR-4 | All user-facing and log text in English |

## 5. Data Source
Hacker News official public API (`hacker-news.firebaseio.com`) — no authentication required, no rate-limit key needed as of this writing.

## 6. Acceptance Criteria
- [ ] Running the crawler once produces a local data file and (if configured) a populated Supabase table
- [ ] Running the crawler a second time does not create duplicate rows for the same story
- [ ] Dashboard loads and displays data with no manual data-file editing required
- [ ] Search and category/author filters visibly narrow the displayed table
- [ ] CSV export button produces a file matching the currently filtered rows

## 7. Out of Scope
- Historical trend analysis across multiple runs (belongs to a separate analytics-focused project, not this pipeline)
- Automatic/scheduled re-runs (belongs to a separate scheduling-focused project, not this pipeline)
- Comment-level content (only comment *counts* are captured, not comment text)
