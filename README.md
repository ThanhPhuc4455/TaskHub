# TaskHub API

TaskHub is an async FastAPI task-management API using SQLAlchemy and PostgreSQL.

## Run locally

```powershell
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

Run the checks with:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest -q
```

## Day 4 authorization

Workspace roles are ordered as `VIEWER < EDITOR < OWNER`. `ADMIN` is a system-wide
role and bypasses workspace membership checks.

| Action | VIEWER | EDITOR | OWNER | ADMIN |
|---|---:|---:|---:|---:|
| View workspace/project | yes | yes | yes | yes |
| Create/update project | no | yes | yes | yes |
| Archive/delete project | no | no | yes | yes |
| Invite/remove/change member role | no | no | yes | yes |
| Delete workspace | no | no | yes | yes |

Users outside a workspace receive `404` so resource existence is not disclosed.
Authenticated users without enough permission receive `403`; missing or invalid
credentials receive `401`; duplicate resources return `409`.

Workspace deletion cascades members and projects at both the ORM relationship and
database foreign-key level. Project deletion consequently cascades its tasks and
labels, and task deletion cascades comments and task-label links.

## Create an ADMIN user

ADMIN creation is intentionally not exposed through public registration. After the
database is migrated, run the seed script from PowerShell:

```powershell
uv run python scripts/create_admin.py `
  --email admin@example.com `
  --full-name "TaskHub Admin" `
  --password "change-this-password"
```

An ADMIN can verify access through `GET /api/v1/admin/workspaces`.

## API groups

- Workspace: `/api/v1/workspaces`
- Members: `/api/v1/workspaces/{workspace_id}/members`
- Projects: `/api/v1/workspaces/{workspace_id}/projects` and `/api/v1/projects/{project_id}`
- ADMIN: `/api/v1/admin/workspaces`
- Tasks: `/api/v1/projects/{project_id}/tasks` and `/api/v1/tasks/{task_id}`
- Labels: `/api/v1/projects/{project_id}/labels` and `/api/v1/labels/{label_id}`
- Comments: `/api/v1/tasks/{task_id}/comments`

## Day 5 task management

Tasks, labels, and comments resolve their owning project and workspace before
authorization. VIEWER can read; EDITOR can create/update/delete tasks and labels
and add comments; comment deletion is limited to the author, workspace OWNER, or
ADMIN. Archived projects are read-only. A task assignee must already be a member
of the workspace, labels cannot cross projects, and duplicate task-label links
return `409`.

Task listing supports `status`, `priority`, `assignee_id`, `page`, and `limit`.
It returns `items`, `total`, `page`, and `limit`, ordered by `created_at DESC,
id DESC`. Invalid input returns `422`; missing resources are `404` and
insufficient role is `403`.

List endpoints accept `page` and `limit` query parameters. `page` starts at 1 and
`limit` is between 1 and 100.

## Migrations

Always run `uv run alembic upgrade head` before starting the application. The
application does not create tables automatically.

## Day 6 runtime features

### Task-list caching

`GET /api/v1/projects/{project_id}/tasks` uses cache-aside Redis caching after
authentication and workspace RBAC have completed. The version key is
`project:{project_id}:tasks:ver`; data keys use the current version and a SHA-256
hash of normalized status, priority, assignee, page, and limit filters. Cached
responses are JSON and expire after `CACHE_TTL_SECONDS` (120 seconds by default).

Redis failures are logged and transparently fall back to the database. Cache
versions are incremented after successful commits for task create/update/delete,
label create/update/delete and attach/detach, project archive/unarchive/delete,
workspace cascade deletion, and profile changes for users who are task assignees.
If Redis invalidation fails after the database commit succeeds, an older cache
entry may remain visible for at most `CACHE_TTL_SECONDS` (120 seconds by
default), after which it expires naturally.
Member removal does not invalidate task lists because it does not change the
assignee summary stored in a task response. No cache key contains caller data:
the response is not user-specific after RBAC authorization.

### Assignment notifications

Task assignment notifications use FastAPI `BackgroundTasks` and an injectable
`NotificationService`. The default implementation logs a safe mail-like event;
it does not log passwords, tokens, or other sensitive data. A notification is
queued after a successful task commit when a task is created with another user
as assignee or when an existing task changes to a new assignee. It is not queued
for unchanged assignments, unassignment, self-assignment, invalid assignees, or
failed writes. Notification failures are caught and logged without changing the
successful API response.

### Request IDs and errors

Every HTTP response includes `X-Request-ID`. A valid client-supplied ID is
preserved; invalid or oversized IDs are replaced with a UUID4. Request logs
contain method, path, status, duration, and request ID, but never authorization
headers or request bodies. Domain, HTTP, validation, and unexpected errors keep
the existing `detail` field and add `code` and `request_id`. Unexpected errors
return a generic 500 message while the full traceback remains server-side.

The test suite uses an injectable fake cache and notification service. A real
Redis integration test can be added separately when Redis is available; the
normal suite does not require a running Redis instance. Run the real Redis
integration tests with:

```powershell
uv run pytest -q -m redis_integration
```

These tests use Redis database 1, skip only when Redis is unavailable, and clean
only their own `project:integration:*` keys with SCAN/DEL.
