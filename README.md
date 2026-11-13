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
