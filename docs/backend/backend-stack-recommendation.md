# Backend Framework And Storage Recommendation

## Version

- MVP

## Task ID

- `MVP-T3 / MVP-T6 / MVP-T8` backend-owned portion only

## Current Branch

- `feat/backend-device-session-foundation`

## Decision Status

- not frozen yet
- this document is a recommendation only
- no backend framework, ORM, or database choice is being made real in this iteration

## What Exists Today

- the repo has Python 3.12 configured in [pyproject.toml](/Users/mac/Desktop/Ai-pet/pyproject.toml)
- the existing executable code is an AI orchestration skeleton under [src/ai_orchestrator](/Users/mac/Desktop/Ai-pet/src/ai_orchestrator)
- there is no established REST framework
- there is no ORM or migration tool in the repo yet
- there is no database adapter or deployed schema baseline yet

## Recommendation Summary

For MVP backend implementation, the most practical default recommendation is:

- runtime language: Python
- API framework: FastAPI
- validation layer: Pydantic
- ORM / SQL layer: SQLAlchemy 2.x
- migration tool: Alembic
- production database: PostgreSQL
- local development database: SQLite only for quick local runs, not as the source of truth for staging or production

## Why This Is The Recommended Shape

### Python

- already aligned with the current repo runtime
- lets backend and AI-adjacent teams share language and deployment primitives
- fastest path from current repository state to a real service

### FastAPI

- low ceremony for MVP
- produces OpenAPI cleanly from route definitions
- straightforward request/response modeling for account, device, bind, session, and admin APIs
- easy to keep one modular monolith before deciding whether to split services later

### SQLAlchemy 2.x + Alembic

- mature path for relational domain models and migrations
- works well for bind/session/admin query workloads
- supports a gradual move from simple CRUD to richer query needs
- keeps persistence details separate from domain services if repository boundaries are respected

### PostgreSQL

- strong fit for operational query patterns in admin and session inspection
- better long-term safety than starting production on SQLite
- supports indexes and query growth for session/admin slices without revisiting core assumptions too early

## Alternatives Considered

### Flask + SQLAlchemy

- workable, but needs more manual setup for schema contracts and typed request/response handling

### Django

- strong batteries included, but heavier than needed for this MVP foundation and less aligned with the existing repo shape

### Pure raw SQL without ORM

- possible for a small MVP, but raises maintenance cost when bind rules, session filters, and admin queries grow

## Recommended Service Shape

If this recommendation is accepted later, keep the MVP as one backend application with clear modules:

- `accounts`
- `devices`
- `bindings`
- `sessions`
- `entitlements`
- `admin_api`

Under that app, preserve the domain split:

- API layer
- service layer
- repository layer
- persistence models

## Recommended Database Shape

Use one relational database with these initial tables:

- `accounts`
- `devices`
- `device_bindings`
- `device_sessions`
- `session_transitions`

Hold off on introducing separate subscription, memory, or safety review tables in this branch.

## What Should Be Frozen Before Real Implementation

- v0 failure codes
- v0 session states
- bind API request/response shape
- admin query field set

These are frozen in [device-session-foundation-v0-freeze.md](/Users/mac/Desktop/Ai-pet/docs/backend/contracts/device-session-foundation-v0-freeze.md).

## What Should Wait Until After Framework Confirmation

- real REST handlers
- real ORM models
- real Alembic migrations
- production config wiring
- DB session lifecycle wiring

## Suggested Next Decision

The control owner should confirm one of these paths:

1. Approve `Python + FastAPI + SQLAlchemy + Alembic + PostgreSQL` as MVP backend baseline.
2. Keep Python, but choose another API/database stack explicitly before repository implementation becomes concrete.

## Risk Notes

- delaying framework choice too long will cause contract drift between backend, frontend, firmware, and admin
- choosing SQLite as the real MVP production database would make admin and session query growth harder than necessary
- choosing a different runtime language now would conflict with the current repo shape and slow execution
