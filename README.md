# Job Monitor v3.1

Scrapes recruitment sources, resolves them into canonical jobs, keeps history, scores
Junior/Entry-level eligibility (location + junior score only), tracks run health, sends an
idempotent daily digest, and shows it all in a dashboard.

## Quick start (local, SQLite)

```bash
python -m venv .venv
.venv/Scripts/activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # set RECIPIENT_EMAIL; SMTP optional

alembic upgrade head              # schema comes from migrations only
python -m backend.cli create-user --email you@example.com --name "Your Name" --admin   # first admin (others can sign up)
python -m backend.cli probe       # hit every live source, print a report, write nothing
python -m backend.cli run         # one full run against the live sources (~3 min)

uvicorn backend.main:app --reload # API on :8000 (also serves frontend/dist if built)
pytest -q
```

Dashboard (dev mode, hot reload, proxies `/api` to :8000):

```bash
cd frontend && npm install && npm run dev    # http://localhost:5173
npm run build                                # -> frontend/dist, served by FastAPI
```

Without SMTP settings, digests are written to `outbox/` as HTML.

## Users, alerts and outreach

* **Accounts**: sign up with email + password (name, junior/experienced) or **Continue with
  Google**; `ALLOW_SIGNUP=false` makes it invite-only (admins create users on the Admin page or
  with `create-user`). Passwords are scrypt-hashed; sessions are random tokens in an HttpOnly,
  SameSite=Lax cookie (only the SHA-256 is stored). State-changing requests also need
  `X-Requested-With: fetch`. 8 failed logins in 15 minutes lock the account for that window.
* **Designated admins**: addresses in `ADMIN_EMAILS` (`.env`, comma-separated) become admins
  as soon as the address is verified - on Google sign-in, on the verification link, or at the
  next login; `python -m backend.cli ensure-admins` promotes existing accounts. An unverified
  sign-up with that address is never promoted.
* **Email verification**: self-registered users get a single-use link (48 h). Until they
  click it the account works, but **no alerts are emailed and outreach is blocked** - both
  would otherwise let anyone point our emails at an address they don't own. Google accounts
  are verified by Google; admin-created accounts are trusted.
* **Google sign-in**: OAuth 2.0 authorization code + PKCE, `state` checked against an
  HttpOnly cookie. A Google login links to an existing account with the same email **only**
  if Google reports the email as verified. Google-only users can add a password later.
  Setup: see `GOOGLE_CLIENT_ID` in `.env.example`.
* **Personal area** (`/me`): profile (junior / experienced), alerts on/off, a private recruiter
  list (name, email, company), and the jobs matching the profile - best first.
* **Alerts**: after each run every user with alerts on gets one email listing new matching
  jobs, government tenders first, then jobs at companies where they saved a recruiter.
  Each job is sent to a user once; a failed send is retried next run.
* **Outreach** ("שלח בקשת סיוע למגייסים"): one personalised email per saved recruiter
  (`שלום <name>, ...`), never a shared/BCC mail. Reply-To is the user. Each
  (user, job, recruiter) is sent at most once; `users.outreach_daily_limit` caps it per day.
* **Admin** (`/admin`): users, logins / failed logins, page views per day, top pages,
  alerts and outreach sent, jobs by source and role, recent runs. No IPs or user agents
  are stored; page paths are stored with ids collapsed (`/jobs/:id`).

## Recruiters, points and subscriptions (config/matching.yaml -> billing)

* **Roles**: `user`, `recruiter`, `admin` (one `role` column; migration 0004 turns every former
  admin into `admin`). Admins grant/revoke the recruiter role on the Admin page
  (`PUT /api/admin/users/{id}` with `{"role": "recruiter"}`); an admin cannot demote themself.
* **Manual postings** (`/recruiter`, recruiters and admins): tender number (unique), ministry,
  title, description, requirements, location. They are evaluated like scraped jobs, appear on
  the main board for every user (badge "פורסם באתר"), are **never merged with scraped jobs and
  never pruned** by the daily refresh.
* **Points**: each posting earns `points_per_manual_job` (at most `max_awarded_posts_per_day`
  awarded postings a day). Every movement is a `point_transactions` row; `users.points_balance`
  is its running sum and changes only through conditional SQL updates, so a balance can never
  be overdrawn by concurrent spends. Deleting a posting reverses its award (refused if the
  points were already spent; an admin removing spam may leave a negative balance).
* **Spending**: a subscription (`subscription_price_points`) or featuring a posting at the top
  of the board (`featured_job_points` for `featured_job_days`).
* **Subscriptions** (`/billing`): one checkout pipeline with two methods - `free` (accepted only
  while `subscription_price_ils` is 0) and `points`. A one-time trial (`trial_days`). Renewing
  early stacks the new period after the current one. A non-zero ILS price needs a payment
  provider that does not exist yet, so a paid price refuses the free bypass instead of giving
  the product away. Prices come from env: `SUBSCRIPTION_PRICE_ILS`, `SUBSCRIPTION_PRICE_POINTS`,
  `POINTS_PER_MANUAL_JOB`. Nothing is gated behind a subscription yet.

## Daily refresh (config/matching.yaml -> retention)

The database holds only jobs the sites still publish. Each run upserts what it found, then
deletes postings a site no longer lists - with their history, evaluations, alert and
outreach records - and deletes jobs left with no posting. Only the latest evaluation per
job is kept. Safeguards:

* Only sites that scraped **successfully** in this run are pruned (a failed or empty
  scrape proves nothing; those jobs wait for the site's next good run).
* If one run would remove more than `retention.max_prune_ratio` (50%) of a site's
  postings, that site is not pruned and the run page shows a warning.
* A job listed by two agencies survives while either still lists it.

## Matching rules (config/matching.yaml)

* **Junior = 0-2 years**: the years a posting requires are parsed from its text ("3 שנות
  ניסיון", "ניסיון של עד שנה", "3-4 שנים", "ללא ניסיון", "3+ years"; lines marked "יתרון" are
  ignored). More than `experience.junior_max_years` (2) is never junior, whatever the keywords.
* **Role type** (from the title): software, data/AI, DevOps, cyber, QA, embedded, hardware,
  product/project, IT - all technology roles are eligible; non-tech (sales, customer service,
  admin, finance, HR, logistics) is `other`: stored, never shown by default. Junior jobs are
  highlighted and pinned first.
* **Relevance** (default sort): junior roles first, then software > QA > embedded > hardware,
  then junior score (`ranking`).
* **Government tenders**: `government.keywords` (מכרז, משרד ממשלתי, ...) mark a job with a badge,
  a filter and top priority in alerts. (This supersedes the v3.1 spec's "no government
  concept" rule, by request.)
* Hebrew seniority words (בכיר, ארכיטקט, ראש צוות, ...) are negative junior keywords.

## Production

**Step-by-step deployment guide: [DEPLOY.md](DEPLOY.md)** (Render + Neon + GitHub Actions,
Google sign-in, email, Search Console, custom domain).

* **Public site / SEO**: `/`, `/login`, `/privacy`, `/terms` are public and indexable (server-rendered
  title/description/canonical/Open Graph); everything behind login and all of `/api/` is `noindex`
  and disallowed in `/robots.txt`; `/sitemap.xml` lists the public pages; unknown paths return 404.
* **Existing data**: `python -m backend.cli copy-data --source sqlite:///job_monitor.db` copies the local
  database into `DATABASE_URL` (refuses a non-empty target).

* **PostgreSQL** via `DATABASE_URL=postgresql+psycopg://...`. SQLite is for local dev/tests only.
* **GitHub Actions**: `.github/workflows/job-monitor.yml` runs daily at **07:00 Israel time**
  (two UTC crons + a gate job that handles summer/winter time), then tests, migrations, run.
  Secrets: `DATABASE_URL`, `RECIPIENT_EMAIL`, `SMTP_*`; variable `PUBLIC_BASE_URL`.
  The workflow refuses non-Postgres URLs.
* **Email**: any SMTP server; Amazon SES via its SMTP endpoint (see `.env.example`).
* The dashboard (API + UI) must be hosted somewhere for users to log in - e.g. the Docker
  image on any container host, with `COOKIE_SECURE=true` behind HTTPS.
* **Docker**: `docker compose up --build`, then `docker compose run --rm app python -m backend.cli run`.

## Layout

```
backend/
  domain/            models, enums, pure services (normalization, identity, matching,
                     evaluation, change detection, retention, run status)
  application/       run_pipeline (orchestration), queries (read side), notification,
                     scraper executor, ports (repository interfaces), dto
  infrastructure/    db (ORM + Alembic migrations), repositories, scrapers (+ shared retry
                     HTTP client), email (renderer, SMTP/file senders)
  api/               FastAPI routes - delegate only
  bootstrap.py       composition root;  cli.py  entry point;  main.py  API app
config/              matching.yaml (business rules), sources.yaml (sources)
frontend/src/        components, pages, services (API + formatting), hooks, types
tests/               unit tests + pipeline/API integration tests on a migrated DB
```

## Live sources

One module per site in `backend/infrastructure/scrapers/sites/`, enabled in `config/sources.yaml`.
Every path used was checked against the site's robots.txt; requests are throttled per host
(`scraper.rate_limit_per_site`) and retried by the shared client.

| Source | How it is read | Notes |
|---|---|---|
| Matrix | WP archive `/jobs/משרה/page/N/` | ~500 jobs |
| HMS | JSON embedded in `/jobs/` | no per-job pages; links go to the board |
| Tigbur | admin-ajax JSON (`tb_get_jobs`) | general staffing: `categories` in config scopes it to IT |
| Aman | paged cards + detail page per job | |
| Horizon | one list page + detail page per job | |
| Comblack | `/categories/all/` (single page) | |
| Consist | `/jobs/?page=N` | |
| Yael | `/jobs/` (single page) | includes Koren Tech |
| GAV Systems (גב מערכות) | WP REST `jobs` + detail page | |
| Ness | public JSON API `GetAllItems` | recruiter names/emails not stored |
| ProLogic | ~50 category pages | no location field -> location read from text |
| SQLink | category pages | no location field -> location read from text |
| One (+ Taldor) | `/careers/` + POST `load_more_jobs` | |
| Malam Team | **disabled** | Cloudflare bot challenge (403) - needs an official feed |
| Log-On | **disabled** | logon.co.il returns 418 to automated clients |

**Behind NetFree or another TLS-inspecting filter?** Certificates are verified with the OS
trust store (`truststore`), so the filter's root CA installed in Windows is honoured.

### Verifying the live integration

```bash
python -m backend.cli probe                     # all sources: status, counts, 2 samples each
python -m backend.cli probe --source Matrix     # one source
pytest tests/test_site_parsers.py -q            # offline parsers vs. captured pages
```

`probe` exits non-zero if any source fails. A `parse_error` saying *"not found - site layout may
have changed"* means the site redesigned: re-capture its fixture in `tests/fixtures/sites/`,
fix the selectors in its module, and re-run the parser tests.

### Adding a source

1. JSON endpoint? Add a `json_api` entry with `url`, `items_path` and `field_map`. No code.
2. Otherwise add `sites/<name>.py` with a `SiteScraper` subclass (`company` = the config `name`),
   keep parsing in pure `parse_*` methods, register it in `sites/__init__.py`, add a trimmed
   fixture + test. Retry, throttling, normalization, matching and scoring are shared - don't
   re-implement them in the scraper.

## Design decisions beyond the spec

* **`job_changes` table**: history (`/api/jobs/{id}/history`) needs persisted change events;
  the listed tables had nowhere to keep them.
* **`junior_scoring` weights in config**: the spec gives keywords + threshold but no weights;
  they're config, not code. Each keyword counts once; score is clamped to 0..1.
* **Canonical content is updated only when a source's own content changes**
  (`source_metadata_hash`), so two sources with slightly different text don't flip-flop
  `CONTENT_UPDATED` every run.
* **Matching requires a corroborating signal**: title similarity ≥ threshold *and* company or
  location equal (and neither conflicting). A title alone never merges jobs.
* **Email idempotency**: claim a `pending` row (unique key) → send → mark `sent`; failed sends
  delete the claim so a later run retries; a claim abandoned by a crash is taken over after
  `email.claim_timeout_minutes`. No email is sent when there are no eligible changes.
* `ZERO_RESULTS` counts as unsuccessful for run status and never proves a site delisted anything.
* `/api/sources` and `/api/activity` were added to feed the Sources page and Recent activity.
* **An agency's second posting never merges into a job that already holds one of its postings**
  (different ids from one agency = different openings). Without this, boilerplate-heavy titles
  ("לארגון פיננסי מוביל דרוש/ה ...") merged unrelated jobs.
* **Stored links are the site's own URLs** (tracking params removed); identity and
  `SOURCE_URL_UPDATED` use the normalized fingerprint, so `www`/slash/utm noise isn't a change.
* **UI is Hebrew, right-to-left**: all strings live in `frontend/src/i18n/he.ts`, including
  display labels for backend status/rule codes.
