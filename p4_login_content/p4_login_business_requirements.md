# Business Requirements — Project 4: Authenticated Crawl

## 1. Business Context
Many real sites gate content behind a login wall. A crawler targeting such a site needs to handle CSRF-protected form login and carry the resulting session forward through every subsequent request — this project builds and proves that mechanism against a safe practice target.

## 2. Objective
Log in programmatically, PROVE the login succeeded (not just assume it from a 200 status), then crawl all paginated content using the authenticated session.

## 3. Functional Requirements
| ID | Requirement |
|----|-------------|
| FR-1 | System shall extract the CSRF token from the login form before submitting credentials |
| FR-2 | System shall submit login credentials via POST with the extracted CSRF token |
| FR-3 | System shall verify login success via a content-based check (not status code alone) |
| FR-4 | System shall reuse the authenticated session across every paginated request |
| FR-5 | System shall capture quote text, author, and tags |
| FR-6 | System shall reject and log any record missing required fields |

## 4. Non-Functional Requirements
| ID | Requirement |
|----|-------------|
| NFR-1 | A single run shall run data-quality checks and login verification automatically |
| NFR-2 | No cost — free tiers only |

## 5. Data Source
quotes.toscrape.com/login — a public practice site for CSRF/session-handling. Any credentials are accepted; content is identical logged in or out (documented limitation, not a defect in this pipeline).

## 6. Acceptance Criteria
- [ ] `python p4_login_pipeline.py` logs in, crawls, validates, saves, and verifies in one command
- [ ] Verification explicitly confirms the "Logout" link is present post-login (proof of session, not just HTTP 200)
- [ ] Re-running the pipeline does not duplicate quote rows
- [ ] Dashboard's filter panel offers a multiselect for every column, consistent with Projects 3+

## 7. Out of Scope
- Demonstrating access-controlled content differences (not possible on this target site)
- Handling 2FA, OAuth, or other auth flows beyond CSRF-token form login
