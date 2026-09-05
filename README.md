# Team Directory

A small people directory built with **Python, FastAPI, PostgreSQL and React**. Viewers explore public profiles; HR manages records and explicitly reveals confidential details. Every authenticated confidential-read attempt leaves an audit record, and a successful read cannot return data until that record is committed.

All people, email addresses, notes and salary figures are fictional. This is a portfolio demonstration, not a system for real employee records.

![Team Directory desktop interface](docs/directory-desktop.png)

## What this demonstrates

- Python API development with FastAPI, typed Pydantic validation and generated OpenAPI.
- PostgreSQL relationships, SQL queries, constraints, indexes and versioned Alembic migrations.
- Argon2 password hashing, expiring JWTs, database-backed permission checks and audit logging.
- React/TypeScript forms, search, filters, pagination and explicit session/error states.
- Real PostgreSQL integration tests, Chromium smoke tests, Docker and GitHub Actions.
- A single-service Cloud Run deployment prepared for Neon PostgreSQL.

## Architecture

```text
Browser: React + TypeScript
     │ same-origin HTTPS, in-memory Bearer token
     ▼
FastAPI: public response schemas + permission checks
     ├── /api/*          application API
     ├── /docs           Swagger UI
     ├── /openapi.json   OpenAPI schema
     ├── /health         process liveness (no DB query)
     └── /people, ...    built React application
     │ SQLAlchemy, bounded connection pool
     ▼
PostgreSQL: local Docker / production Neon
     ▲
Alembic migration job (separate from application startup)
```

```mermaid
erDiagram
    PERSON ||--o{ EMPLOYMENT : has
    CLASSIFICATION ||--o{ EMPLOYMENT : categorizes
    PERSON ||--o{ COMPLIANCE_RECORD : completes
    USER ||--o{ AUDIT_EVENT : requests
    PERSON o|--o{ AUDIT_EVENT : targets
    PERSON {
        int id PK
        string name
        string work_email UK
        string department
        text private_notes "confidential"
    }
    EMPLOYMENT {
        int id PK
        int person_id FK
        int classification_id FK
        string job_title
        date start_date
        date end_date
        string status
        decimal salary "confidential CAD"
    }
    CLASSIFICATION {
        int id PK
        string name UK
    }
    COMPLIANCE_RECORD {
        int id PK
        int person_id FK
        string requirement
        string status
        date completion_date
        date expiry_date
    }
    USER {
        int id PK
        string username UK
        string password_hash
        string role
    }
    AUDIT_EVENT {
        int id PK
        int actor_id FK
        int target_person_id FK "nullable if missing"
        int requested_person_id
        string action
        json field_names
        timestamp timestamp
        string outcome
    }
```

The backend is deliberately small: `models.py` describes storage, `schemas.py` defines allowed input/output, `security.py` authenticates users and maps permissions, and `api.py` contains the queries and endpoints. There is no generic repository or service framework to learn first.

## Run locally with Docker

Prerequisites: Docker Engine/Desktop with Compose, plus Python 3 to generate local credentials. Run from the repository root:

```bash
python3 scripts/init_env.py
docker compose up -d db --wait
docker compose build app
docker compose run --rm app alembic upgrade head
docker compose run --rm app python -m app.seed
docker compose up -d app
```

The environment generator refuses to overwrite an existing `.env`. It creates random local database credentials, a JWT secret, and separate Viewer/HR passwords; the file is ignored by Git and excluded from Docker/Cloud Build contexts. Alternatively copy `.env.example` to `.env` and replace every placeholder. Use URL-safe characters for the local PostgreSQL password, or percent-encode it inside the connection URL.

Open [the application](http://localhost:8080), [API documentation](http://localhost:8080/docs), or [OpenAPI](http://localhost:8080/openapi.json). Choose **Viewer** or **HR** and enter the corresponding `DEMO_VIEWER_PASSWORD` or `DEMO_HR_PASSWORD` from your local `.env`.

The seed command creates **18 fictional people**, employment and training records, three classifications, and two users (`viewer`, `hr`). It can be run repeatedly: existing people, records and passwords are preserved. It adds missing seeded people but does not repair or overwrite edits to existing profiles. Migrations are always an explicit step, never part of app startup.

```bash
docker compose logs -f app
docker compose stop             # preserve database contents
docker compose down            # remove containers; keep the database volume
```

Do not use `down -v` unless you intend to erase the local database.

## Develop without rebuilding Docker

Prerequisites: Python 3.12+, [uv](https://docs.astral.sh/uv/), Node.js 22+, npm and Docker for PostgreSQL.

```bash
# Root directory; skip init_env if .env already exists.
python3 scripts/init_env.py
docker compose up -d db --wait
uv sync --project backend --frozen --python 3.12
npm ci --prefix frontend
set -a
source .env
set +a
backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend backend/.venv/bin/python -m app.seed
backend/.venv/bin/uvicorn app.main:app --app-dir backend --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm run dev
```

Open [Vite on localhost:5173](http://localhost:5173). Its proxy forwards `/api`, `/docs`, `/openapi.json`, `/redoc` and `/health` to FastAPI. Production serves everything from FastAPI on one origin; CORS middleware is unnecessary. After `npm run build --prefix frontend`, FastAPI also serves the built UI directly at port 8000 (restart FastAPI to mount newly created assets).

### Migrations

With environment variables loaded, from the root:

```bash
backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
backend/.venv/bin/alembic -c backend/alembic.ini current
backend/.venv/bin/alembic -c backend/alembic.ini check
# After intentionally changing a model:
backend/.venv/bin/alembic -c backend/alembic.ini revision --autogenerate -m 'Describe change'
```

Review generated migrations before applying them. The initial migration contains concrete table definitions and a reverse migration. Never run downgrade against production without a backup and a data-loss review.

## Permissions and demo accounts

| Permission / scope | Viewer | HR |
| --- | --- | --- |
| `directory:read`: directory, profiles, employment, training, categories | Yes | Yes |
| `records:write`: create/update records, delete related records/categories | No | Yes |
| `confidential:read`: explicitly reveal notes and salary | No | Yes |
| `confidential:write`: update notes and salary | No | Yes |
| `audit:read`: view access history | No | Yes |

Roles are assigned to users in PostgreSQL. Every request reloads the user and derives permissions from the stored role. A supplied role or scope in a token cannot promote a Viewer. Swagger's **Authorize** uses the same demo credentials; its requested scopes do not grant additional permissions.

Tokens expire after 30 minutes by default. React keeps them only in memory, clears them on sign-out/expiry/401, and clears confidential data when a profile unmounts or the session ends. Reloading the page requires signing in again. There are no refresh tokens or persistent browser credentials.

## API examples

Use the commands below in Bash/Zsh with `jq` installed and `.env` loaded. Tokens remain shell variables; do not paste them into logs or commit them.

```bash
BASE=http://localhost:8080
TOKEN=$(curl --fail --silent "$BASE/api/auth/token" \
  --data-urlencode username=viewer \
  --data-urlencode "password=$DEMO_VIEWER_PASSWORD" | jq -r .access_token)

curl --fail --silent "$BASE/api/auth/me" -H "Authorization: Bearer $TOKEN" | jq
curl --fail --silent "$BASE/api/people?q=avery&page=1&page_size=9" \
  -H "Authorization: Bearer $TOKEN" | jq
curl --fail --silent "$BASE/api/people/1" -H "Authorization: Bearer $TOKEN" | jq

# Viewer: expect 403; the authenticated attempt is committed to audit history.
curl --silent -i "$BASE/api/people/1/confidential" -H "Authorization: Bearer $TOKEN"

TOKEN=$(curl --fail --silent "$BASE/api/auth/token" \
  --data-urlencode username=hr \
  --data-urlencode "password=$DEMO_HR_PASSWORD" | jq -r .access_token)

# HR: explicit, audited confidential read (synthetic data only).
curl --fail --silent "$BASE/api/people/1/confidential" -H "Authorization: Bearer $TOKEN" | jq
curl --fail --silent "$BASE/api/audit?person_id=1" -H "Authorization: Bearer $TOKEN" | jq

# Ordinary creation/update responses never contain confidential values.
curl --fail --silent "$BASE/api/people" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Taylor Example","work_email":"taylor@example.com","department":"Engineering"}' | jq
unset TOKEN
```

The full endpoint contract is at `/docs`. Key routes:

| Routes | Operations |
| --- | --- |
| `/api/auth/token`, `/api/auth/me` | POST login, GET current user |
| `/api/people`, `/api/departments` | GET directory/options; POST people |
| `/api/people/{id}` | GET public profile; PUT public fields |
| `/api/people/{id}/employments` | POST employment including initial salary |
| `/api/people/{id}/employments/{employment_id}` | PUT public fields; DELETE record |
| `/api/people/{id}/compliance`, `.../{record_id}` | POST, PUT, DELETE training |
| `/api/classifications`, `.../{id}` | GET, POST, PUT, DELETE categories |
| `/api/people/{id}/confidential` | GET audited reveal; PATCH private notes (204) |
| `/api/people/{id}/employments/{employment_id}/salary` | PATCH salary (204) |
| `/api/audit` | GET paginated access history, optional `person_id` |

Directory filters: `q` (case-insensitive literal name substring), exact `department`, `status` (`active`, `on_leave`, `ended`) and `classification_id`. Employment filters apply to the **same** employment row, including historical rows. Stable alphabetical ordering uses person ID as the tie-breaker; filtering does not duplicate people with multiple employments. Page sizes are limited to 100.

Error responses use `detail`: **401** invalid session, **403** forbidden, **404** missing record, **409** uniqueness/relationship conflict, **422** invalid request, **503** unavailable database. Validation errors include safe field locations/types but omit submitted input and database exception text.

## Test and check

Tests require a dedicated PostgreSQL database with a name ending in `_test`. They truncate its application tables. The test container uses a separate port, database and temporary volume; development data is untouched. Run backend and browser suites sequentially because each resets the test database.

```bash
docker compose --profile test up -d test-db --wait
export TEST_DATABASE_URL='postgresql+psycopg://team:test-only-password@127.0.0.1:15433/team_directory_test'

backend/.venv/bin/ruff check backend scripts
backend/.venv/bin/ruff format --check backend scripts
npm run format:check --prefix frontend
npm run build --prefix frontend
backend/.venv/bin/pytest backend/tests -q

cd frontend
npx playwright install chromium
npm run test:e2e
```

Alembic creates the test schema; no SQLite substitute or `create_all` is used. Backend tests cover authentication/expiry, CRUD, combined filtering/pagination, direct SQL constraints, date rules, missing/malformed records, every Viewer mutation boundary, response leaks, successful/denied auditing, protected history and audit-write failure. Browser tests use the real API/PostgreSQL for login, search, role differences and HR forms. Only the browser's server-failure/session-expiry presentations use intercepted responses; real token expiry is covered in backend tests.

The browser suite starts its own backend on 8001 and Vite on 5174, resets/seeds the test database, and closes both servers afterward. It uses fixed **test-only** passwords, never the development `.env` credentials. Traces are disabled to avoid storing bearer tokens. Failure screenshots contain synthetic data only.

GitHub Actions repeats lint/format checks, builds React, migrates/tests PostgreSQL, runs Chromium smoke tests, and builds the Docker image. [Local verification details](docs/VERIFICATION.md) record actual results and any environment limitations; configuring a workflow is not the same as observing a hosted CI run.

## A three-minute demonstration

1. Sign in as **Viewer**, search “Avery,” and open the profile. Show employment and training. Point out the HR-only confidential section and absence of editing controls.
2. Use the Viewer API request above to demonstrate that bypassing the UI still gets a **403**.
3. Sign out, then sign in as **HR**. Edit a public field or add a synthetic training requirement. Confidential details are still hidden when the profile opens.
4. Choose **Reveal confidential details**. Explain that this request succeeds only after the audit event commits. Hide the details again.
5. Open **Access history**. Show the Viewer denial and HR success, actor, person, timestamp and requested field names. Neither notes nor salary values appear in history.
6. Open `/docs` to show the typed API and permission scopes, then show the PostgreSQL-backed test suite.

## Decisions and limitations

- One fictional organization; departments are plain text, not a managed table. Names/department casing is preserved; work emails and classification names are normalized to lowercase. Work emails are unique, but email ownership is not verified.
- Employment is a history with potentially overlapping roles. Status is explicit, not inferred from today's date. End dates cannot precede start dates, but an `ended` status does not require a date because it may be unknown. This is not payroll: all salary amounts are synthetic annualized CAD values.
- One training requirement per person (case-sensitive); completed records require a completion date. Pending records have no dates. Expiry cannot precede completion, and expired completions remain completed rather than automatically changing status.
- People and users are not deleted through the API, preserving audit references. Employment/compliance and unused classifications support API deletion; the UI focuses on create/edit workflows. Linked classifications cannot be deleted. Public-field updates use PUT with all public fields; confidential values have separate PATCH endpoints.
- Notes/salary are excluded through explicit response models, including create/update responses. A reveal returns both kinds of confidential data, records requested field names and commits synchronously; it is not a background logging task. Denied requests for missing person IDs are also logged without a broken FK. Unauthenticated requests and malformed IDs are rejected before this audit path.
- Audit history has no mutation API, but this demo's database owner can alter it. It is not a tamper-proof compliance archive. Only confidential **reads** are audited, not all HR writes. Review timestamps and never treat the fictional records as legal compliance evidence.
- No self-registration, password reset, MFA, refresh tokens, server-side token revocation, account lockout, distributed rate limiter, or multi-tenant isolation. Password hashes use Argon2; no passwords, JWTs, salaries or notes are intentionally logged. API responses are `no-store`, and the bundled UI has a restrictive CSP. `/docs` uses FastAPI's CDN assets and is intentionally public.
- Limit access to demo credentials before public deployment. Anyone given the HR account can modify the synthetic workspace. A real employee system would need identity management, abuse controls, least-privilege DB roles, encryption/access policy review, tamper-resistant audit storage, retention rules, backups and recovery testing.
- Updates are last-write-wins. There is no optimistic locking. Name substring search can scan rows; the lowercase name index supports alphabetical ordering, not arbitrary substring acceleration. This is intentional for a tiny demo.

## Cloud deployment

[The Cloud Run + Neon guide](docs/DEPLOYMENT.md) contains exact build, secret, migration-job, seed-job and service-deployment commands. The initial service configuration uses request-based billing, minimum instances **0**, maximum instances **2**, a pool of **2** connections per process, and no pool overflow. Migrations run separately before a new service revision receives traffic. It also explains how to set minimum instances to **1** and the startup/cost tradeoff.

Deployment preparation does **not** create cloud resources, publish the app, or push Git commits. Those actions require a separate explicit go-ahead.

## Troubleshooting and Git workflow

- **Login fails:** usernames are `viewer` and `hr`; use the passwords that were present when seeding first created each user. Changing `.env` and re-running the idempotent seed does not reset existing passwords. For a fresh disposable demo, create a new empty database and migrate/seed it.
- **Database unavailable:** confirm Docker is running and `docker compose ps` reports a healthy `db`. Host processes use port **15432**; the app container uses **db:5432**. Test processes use **15433**. Avoid accidentally setting `DATABASE_URL` to the wrong host.
- **Frontend build missing:** run `npm run build --prefix frontend` and restart FastAPI, or use Vite during development. Unknown API URLs and assets intentionally return JSON 404s, not the SPA.
- **Browser test cannot launch:** install its matching Chromium with `npx playwright install chromium`; Linux may need `--with-deps`. If your browser cache is elsewhere, use the same `PLAYWRIGHT_BROWSERS_PATH` for install and tests.
- **Docker base image timeout:** retry the pull/build after checking Docker registry connectivity. The host Python/Vite development path can still work independently.
- **Unexpected sign-out after reload:** expected; tokens are deliberately not stored in `localStorage`, `sessionStorage` or cookies.
- **Confidential read returns 503:** no values were returned because the database/audit commit failed. Restore database availability and retry.

Keep `.env`, virtual environments, build outputs, and test artifacts out of Git. A normal local workflow is `git switch -c feature/short-description`, make a focused change, run the checks above, inspect `git diff`, then commit the intended files. Commit `backend/uv.lock`, `frontend/package-lock.json`, and reviewed migrations. Add a remote/push only when you choose to publish the repository.
