# TaskHub API

TaskHub is an asynchronous FastAPI task-management API. It provides authentication,
workspace RBAC, projects, tasks, labels, comments, Redis task-list caching, request
IDs, structured errors, and background assignment notifications.

## Stack

- Python 3.12 and FastAPI
- SQLAlchemy 2.x async + asyncpg
- PostgreSQL 16
- Redis 7
- Alembic migrations
- Pydantic v2 and pydantic-settings
- Docker multi-stage build and Docker Compose

## Repository layout

```text
app/
  api/              FastAPI dependencies, routers, and endpoints
  core/             settings, database, cache, logging, middleware, errors
  models/           SQLAlchemy models and enums
  repositories/     database access
  schemas/          request and response schemas
  services/         business rules and authorization
alembic/            database migrations
tests/              unit, API, PostgreSQL, and Redis integration tests
Dockerfile          multi-stage production image
docker-compose.yml  app + PostgreSQL + Redis stack
```

## Environment variables

Copy `.env.example` to `.env` (local host execution uses `127.0.0.1`). Secrets are examples only;
replace them locally and never commit `.env`.

| Name | Required | Default | Example |
|---|---:|---|---|
| `APP_ENV` | no | `development` (Compose: `production`) | `development` |
| `TASKHUB_DEBUG` | no | `false` | `true` |
| `LOG_LEVEL` | no | `INFO` | `INFO` |
| `DATABASE_URL` | Local only | — | `postgresql+asyncpg://taskhub:password@127.0.0.1:5432/taskhub` |
| `SECRET_KEY` | yes | — | `a-long-local-secret-32-chars-long` |
| `DB_ECHO` | no | `false` | `false` |
| `REDIS_URL` | no | `redis://127.0.0.1:6379/0` | `redis://127.0.0.1:6379/0` |
| `CACHE_TTL_SECONDS` | no | `120` | `120` |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | no | `1.0` | `1.0` |
| `REDIS_SOCKET_TIMEOUT` | no | `1.0` | `1.0` |
| `SMTP_ENABLED` | no | `false` | `false` |
| `SMTP_HOST` | if SMTP enabled | — (Compose: `mailpit`) | `127.0.0.1` |
| `SMTP_PORT` | no | `1025` | `1025` |
| `SMTP_USERNAME` | no | — | `smtp-user` |
| `SMTP_PASSWORD` | no | — | `smtp-password` |
| `SMTP_USE_TLS` | no | `false` | `false` |
| `SMTP_START_TLS` | no | `false` | `false` |
| `SMTP_TIMEOUT_SECONDS` | no | `10` | `10` |
| `SMTP_FROM_ADDRESS` | if SMTP enabled | — (Compose: `taskhub@example.local`) | `taskhub@example.local` |
| `MAILPIT_WEB_PORT` | Compose only | `8025` | `8025` |
| `APP_PORT` | Compose only | `8001` | `8001` |
| `POSTGRES_DB` | Compose only | — | `taskhub` |
| `POSTGRES_USER` | Compose only | — | `taskhub` |
| `POSTGRES_PASSWORD` | Compose only | — | local password |

`APP_ENV` accepts `development`, `test`, or `production`. In `.env.example`, `APP_ENV` is commented out by default (`# APP_ENV=development`). In Docker Compose, `APP_ENV` defaults to `production`. Production strictly requires a non-default `SECRET_KEY` of at least 32 characters. `LOG_LEVEL` accepts `DEBUG`, `INFO`, `WARNING`, or `ERROR`; production defaults to `INFO`. `TASKHUB_DEBUG` enables debug mode explicitly (`False` by default).

## Run locally

With `.env` pointing at a reachable PostgreSQL and Redis instance:

```powershell
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The lightweight health endpoint is available at `GET http://127.0.0.1:8000/health` (returns `{"status":"ok"}` without querying the database). The interactive API documentation is available at `http://127.0.0.1:8000/docs` and ReDoc at `http://127.0.0.1:8000/redoc`.

## Run with Docker Compose

After setting the variables from `.env.example`:

> [!IMPORTANT]
> Because Docker Compose defaults to `APP_ENV=production`, setting a strong `SECRET_KEY` (at least 32 characters, not matching default sample keys) in `.env` is required. The application container will fail startup validation if `SECRET_KEY` is weak or missing.

Start the application stack:

```powershell
docker compose -p taskhub_day7 up -d --build
Start-Sleep -Seconds 10
docker compose -p taskhub_day7 ps
docker compose -p taskhub_day7 logs app
```

The Compose app runs by default with `APP_ENV=production` (requiring a non-default `SECRET_KEY` of at least 32 characters). To run Compose in development mode, uncomment `APP_ENV=development` in `.env` or override `APP_ENV` in your environment (for example, `$env:APP_ENV = "development"`).

To run development services (such as Mailpit for local email inspection), include `--profile dev`:

```powershell
docker compose -p taskhub_day7 --profile dev up -d --build
```

Compose automatically constructs `DATABASE_URL` from `POSTGRES_USER`,
`POSTGRES_PASSWORD`, and `POSTGRES_DB`, and sets `REDIS_URL` to internal service `redis://redis:6379/0`.
The Compose app waits for healthy PostgreSQL and Redis, runs `alembic upgrade head`,
then starts Uvicorn. Only the application port (`8001`) is published to the host by default;
when `--profile dev` is enabled, Mailpit web interface (`8025`) is also published at `http://127.0.0.1:8025`.
PostgreSQL and Redis communicate internally over the compose network without exposing host ports.

When running via Compose, the healthcheck endpoint is available at `GET http://127.0.0.1:8001/health` and docs at `http://127.0.0.1:8001/docs`.

### Stop and clean up Compose

To stop running containers:

```powershell
docker compose -p taskhub_day7 down
```

To stop containers and remove persistent volumes (warning: deletes all database data):

```powershell
docker compose -p taskhub_day7 down -v
```

## Create an ADMIN user

ADMIN creation is intentionally not exposed through public registration.
In a running Docker Compose environment, create an ADMIN user with:

```powershell
docker compose -p taskhub_day7 exec app python scripts/create_admin.py `
  --email admin@example.com `
  --full-name "TaskHub Admin" `
  --password "change-this-password-32-chars-ok"
```

Or when running locally:

```powershell
uv run python scripts/create_admin.py `
  --email admin@example.com `
  --full-name "TaskHub Admin" `
  --password "change-this-password-32-chars-ok"
```

## Tests and quality checks

Use a disposable review database for PostgreSQL integration tests. Replace `password` with your local PostgreSQL password, and adjust the port (such as `5434` or `5432`) to match your PostgreSQL server instance:

```powershell
$reviewDb = "postgresql+asyncpg://taskhub:password@127.0.0.1:5434/taskhub_review"
$env:DATABASE_URL = $reviewDb
$env:REVIEW8_DATABASE_URL = $reviewDb
$env:REVIEW9_DATABASE_URL = $reviewDb
$env:REVIEW9_MIGRATION_DATABASE_URL = $reviewDb
$env:REVIEW10_DATABASE_URL = $reviewDb
$env:REVIEW11_DATABASE_URL = $reviewDb
$env:REVIEW12_DATABASE_URL = $reviewDb
uv run pytest -rs
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run alembic upgrade head
uv run alembic check
```

## API example

Run the local server first, then execute this PowerShell example:

```powershell
$base = "http://127.0.0.1:8000"
$email = "demo-$([Guid]::NewGuid().ToString('N'))@example.com"
$password = "password123"
$user = Invoke-RestMethod -Method Post "$base/api/v1/auth/register" `
  -ContentType "application/json" `
  -Body (@{email=$email; full_name="Demo User"; password=$password} | ConvertTo-Json)
$token = Invoke-RestMethod -Method Post "$base/api/v1/auth/login" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body @{username=$email; password=$password}
$headers = @{Authorization="Bearer $($token.access_token)"}
$workspace = Invoke-RestMethod -Method Post "$base/api/v1/workspaces" `
  -Headers $headers -ContentType "application/json" `
  -Body (@{name="Demo workspace"} | ConvertTo-Json)
$project = Invoke-RestMethod -Method Post "$base/api/v1/workspaces/$($workspace.id)/projects" `
  -Headers $headers -ContentType "application/json" `
  -Body (@{name="Demo project"} | ConvertTo-Json)
$task = Invoke-RestMethod -Method Post "$base/api/v1/projects/$($project.id)/tasks" `
  -Headers $headers -ContentType "application/json" `
  -Body (@{title="First task"} | ConvertTo-Json)
$task
```

## Authorization and errors

Workspace roles are ordered `VIEWER < EDITOR < OWNER`. `ADMIN` is system-wide and
bypasses workspace membership checks. Users outside a workspace receive `404` so
resource existence is not disclosed; authenticated users without enough permission
receive `403`.

Every error response uses the envelope below. Validation errors use a list in
`detail`; domain and HTTP errors use a string:

```json
{
  "detail": "Project 42 not found",
  "code": "not_found",
  "request_id": "trace-123"
}
```

Every response has an `X-Request-ID` header. Application and server logs (including
Uvicorn) include `request_id` in their log output, and redact sensitive fields
(Authorization tokens, passwords, and email addresses).

## Task-list cache

`GET /api/v1/projects/{project_id}/tasks` uses Redis cache-aside after authentication
and RBAC. The version key is `project:{project_id}:tasks:ver`; invalidation increments
that key with `INCR`. Data keys include the project, cache version, normalized filters,
assignee, page, and limit. Cached values are JSON responses with `items`, `total`,
`page`, and `limit`, and expire after `CACHE_TTL_SECONDS`.

Redis read/write failures are logged and fall back to PostgreSQL. Invalidation runs
after successful database commits. If invalidation fails after a commit, an older
cache entry can remain for at most `CACHE_TTL_SECONDS`.

## Notifications

Assignment notifications use FastAPI `BackgroundTasks`. SMTP is disabled by default;
when enabled, configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
`SMTP_USE_TLS`, `SMTP_START_TLS`, `SMTP_TIMEOUT_SECONDS`, and `SMTP_FROM_ADDRESS`.
Notifications are queued only when a task is assigned to another user or changed to a new assignee.

For local testing, start the Mailpit service with `docker compose -p taskhub_day7 --profile dev up -d`.
Mailpit accepts SMTP on the internal `mailpit:1025` address and its web UI is available at
`http://127.0.0.1:8025`. Set `SMTP_ENABLED=true`, `SMTP_HOST=mailpit`, `SMTP_PORT=1025`,
`SMTP_USE_TLS=false`, and `SMTP_START_TLS=false` in the compose environment.
Notification send failures are logged without the recipient address and do not fail the API request.

## Migrations

Run migrations before starting the application:

```powershell
uv run alembic upgrade head
```

The application does not create PostgreSQL tables automatically.
