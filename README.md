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

Copy `.env.example` to `.env` for local Compose usage. Secrets are examples only;
replace them locally and never commit `.env`.

| Name | Required | Default | Example |
|---|---:|---|---|
| `APP_ENV` | no | `development` | `development` |
| `LOG_LEVEL` | no | `INFO` | `INFO` |
| `DATABASE_URL` | yes | — | `postgresql+asyncpg://taskhub:password@db:5432/taskhub` |
| `SECRET_KEY` | yes | — | `a-long-local-secret` |
| `DB_ECHO` | no | `false` | `false` |
| `REDIS_URL` | no | `redis://127.0.0.1:6379/0` | `redis://redis:6379/0` |
| `CACHE_TTL_SECONDS` | no | `120` | `120` |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | no | `1.0` | `1.0` |
| `REDIS_SOCKET_TIMEOUT` | no | `1.0` | `1.0` |
| `APP_PORT` | Compose only | `8001` | `8001` |
| `POSTGRES_PORT` | Compose only | `5435` | `5435` |
| `REDIS_PORT` | Compose only | `6380` | `6380` |
| `POSTGRES_DB` | Compose only | — | `taskhub` |
| `POSTGRES_USER` | Compose only | — | `taskhub` |
| `POSTGRES_PASSWORD` | Compose only | — | local password |

`APP_ENV` accepts `development`, `test`, or `production`. Production rejects a
missing, short, or sample `SECRET_KEY`. `LOG_LEVEL` accepts `DEBUG`, `INFO`,
`WARNING`, or `ERROR`; production defaults to `INFO`. `TASKHUB_DEBUG` can enable
debug mode explicitly, while the default is `False`.

## Run locally

With `.env` pointing at a reachable PostgreSQL and Redis instance:

```powershell
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API documentation is available at `http://127.0.0.1:8000/docs` and ReDoc at
`http://127.0.0.1:8000/redoc`.

## Run with Docker Compose

After setting the variables from `.env.example`:

```powershell
docker compose -p taskhub up -d --build
Start-Sleep -Seconds 10
docker compose -p taskhub ps
docker compose -p taskhub logs app
docker compose -p taskhub down -v
```

The Compose app waits for healthy PostgreSQL and Redis, runs `alembic upgrade head`,
then starts Uvicorn. The default host ports are `8001`, `5435`, and `6380` so they
do not use the usual development ports.

## Tests and quality checks

Use a disposable review database for PostgreSQL integration tests. The following
PowerShell setup makes all PostgreSQL test variables point to the same review DB:

```powershell
$reviewDb = "postgresql+asyncpg://taskhub:password@127.0.0.1:5434/taskhub_review"
$env:DATABASE_URL = $reviewDb
$env:REVIEW8_DATABASE_URL = $reviewDb
$env:REVIEW9_DATABASE_URL = $reviewDb
$env:REVIEW9_MIGRATION_DATABASE_URL = $reviewDb
$env:REVIEW10_DATABASE_URL = $reviewDb
$env:REVIEW11_DATABASE_URL = $reviewDb
uv run pytest -rs
uv run ruff check .
uv run ruff format --check .
uv run mypy .
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

Every response has an `X-Request-ID` header. Logs include request ID, method, path,
status, and duration, and redact Authorization, passwords, and full email addresses.

## Task-list cache

`GET /api/v1/projects/{project_id}/tasks` uses Redis cache-aside after authentication
and RBAC. The version key is `project:{project_id}:tasks:ver`; invalidation increments
that key with `INCR`. Data keys include the project, cache version, normalized filters,
assignee, page, and limit. Cached values are JSON responses with `items`, `total`,
`page`, and `limit`, and expire after `CACHE_TTL_SECONDS`.

Redis read/write failures are logged and fall back to PostgreSQL. Invalidation runs
after successful database commits. If invalidation fails after a commit, an older
cache entry can remain for at most `CACHE_TTL_SECONDS`.

## Background notifications

Assignment notifications use FastAPI `BackgroundTasks` and are currently simulated
by safe log messages. No SMTP integration is included. Notifications are queued only
when a task is assigned to another user or changed to a new assignee; notification
failures do not fail the API request.

## Migrations

Run migrations before starting the application:

```powershell
uv run alembic upgrade head
```

The application does not create PostgreSQL tables automatically.
