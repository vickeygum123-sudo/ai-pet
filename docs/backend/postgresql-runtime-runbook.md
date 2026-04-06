# PostgreSQL Runtime Runbook

## Version

- MVP

## Task ID

- `MVP-T3 / MVP-T6 / MVP-T8` backend-owned portion only

## Current Branch

- `feat/backend-device-session-foundation`

## Purpose

This runbook explains how the current backend foundation should be pointed at PostgreSQL for formal MVP runtime use.

It does not add deployment automation or production auth.

## What Is Ready Now

- SQLAlchemy ORM models exist
- Alembic initial migration exists
- `BACKEND_DATABASE_URL` is the runtime database env var
- local SQLite remains supported for development verification

## Expected PostgreSQL URL

Use `BACKEND_DATABASE_URL` in standard SQLAlchemy form:

```bash
export BACKEND_DATABASE_URL="postgresql+psycopg://app_user:app_password@localhost:5432/ai_pet_backend"
```

## Current Gap

The repository does not yet include a PostgreSQL driver dependency.

For real PostgreSQL runtime, one of these still needs to be added in a follow-up backend-only task:

- `psycopg[binary]`
- or `asyncpg` if the stack later moves to async SQLAlchemy

For the current synchronous stack recommendation, `psycopg[binary]` is the more direct fit.

## Migration Commands

From the repo root:

```bash
BACKEND_DATABASE_URL="postgresql+psycopg://app_user:app_password@localhost:5432/ai_pet_backend" \
PYTHONPATH=src \
python3 -m alembic -c alembic.ini upgrade head
```

Check current revision:

```bash
BACKEND_DATABASE_URL="postgresql+psycopg://app_user:app_password@localhost:5432/ai_pet_backend" \
PYTHONPATH=src \
python3 -m alembic -c alembic.ini current
```

## SQLite Local Development Example

```bash
export BACKEND_DATABASE_URL="sqlite:///./backend_foundation.db"
```

SQLite is acceptable for:

- local API bring-up
- migration smoke tests
- repository and API integration tests

SQLite is not the intended formal MVP runtime database.

## Formal MVP PostgreSQL Still Missing

- PostgreSQL driver dependency
- environment-specific config management
- app server runtime command and deployment wrapper
- DB backup / restore procedure
- connection pool sizing defaults
- production secrets handling
- staging environment verification against PostgreSQL

## Recommendation

Treat the current API and migration set as the MVP backend schema baseline candidate, but do not mark PostgreSQL runtime “ready” until:

1. a PostgreSQL driver is added
2. migration is executed successfully against PostgreSQL
3. API smoke tests are run against PostgreSQL-backed startup
