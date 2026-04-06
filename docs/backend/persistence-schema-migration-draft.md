# Persistence Schema And Migration Draft

## Version

- MVP

## Task ID

- `MVP-T3 / MVP-T6 / MVP-T8` backend-owned portion only

## Current Branch

- `feat/backend-device-session-foundation`

## Status

- draft only
- relational persistence draft
- not bound yet to a concrete ORM or migration tool

## Goal

Prepare the first persistence abstraction and schema direction for:

- account
- device
- binding
- session
- session transition
- entitlement snapshot by account tier

## Repository Boundaries

The service layer should depend on repository interfaces, not ORM models directly.

Initial repository ownership:

- `AccountRepository`
- `DeviceRepository`
- `BindingRepository`
- `SessionRepository`

This split is enough for the MVP foundation. Add more only after the real framework is confirmed.

## Relational Tables Draft

### `accounts`

| Column | Type | Notes |
| --- | --- | --- |
| `account_id` | string / uuid-like | primary key |
| `auth_subject` | string | unique |
| `display_name` | string nullable | |
| `default_role_id` | string | |
| `entitlement_tier` | string | `free` or `subscribed` |
| `created_at` | timestamp | |

Indexes:

- unique on `auth_subject`

### `devices`

| Column | Type | Notes |
| --- | --- | --- |
| `device_id` | string | primary key |
| `hardware_model` | string | |
| `firmware_version` | string | |
| `pairing_code` | string | unique while active |
| `device_status` | string | |
| `bind_status` | string | |
| `owner_account_id` | string nullable | foreign key to `accounts.account_id` |
| `created_at` | timestamp | |
| `last_online_at` | timestamp nullable | |

Indexes:

- index on `owner_account_id`
- index on `bind_status`
- index on `last_online_at`

### `device_bindings`

| Column | Type | Notes |
| --- | --- | --- |
| `binding_id` | string / uuid-like | primary key |
| `account_id` | string | foreign key |
| `device_id` | string | foreign key |
| `status` | string | `bound` or `unbound` |
| `bound_at` | timestamp | |
| `unbound_at` | timestamp nullable | |

Indexes:

- index on `account_id`
- index on `device_id`
- composite index on `device_id, status`

Constraint note:

- only one active binding per device should exist at a time

### `device_sessions`

| Column | Type | Notes |
| --- | --- | --- |
| `session_id` | string / uuid-like | primary key |
| `account_id` | string | foreign key |
| `device_id` | string | foreign key |
| `role_id` | string | |
| `entitlement_tier` | string | snapshot |
| `state` | string | frozen v0 state set |
| `asr_status` | string | |
| `llm_status` | string | |
| `tts_status` | string | |
| `safety_flag` | boolean | |
| `fallback_used` | boolean | |
| `continuity_recall_used` | boolean | |
| `first_response_latency_ms` | integer nullable | |
| `failure_code` | string nullable | frozen v0 failure code set |
| `firmware_version` | string | |
| `started_at` | timestamp | |
| `ended_at` | timestamp nullable | |

Indexes:

- index on `account_id`
- index on `device_id`
- index on `state`
- index on `failure_code`
- index on `started_at`

### `session_transitions`

| Column | Type | Notes |
| --- | --- | --- |
| `transition_id` | string / uuid-like | primary key |
| `session_id` | string | foreign key |
| `state` | string | frozen v0 state set |
| `recorded_at` | timestamp | |
| `notes` | text nullable | |

Indexes:

- index on `session_id`
- index on `recorded_at`

## Migration Draft Sequence

### Migration 0001

- create `accounts`
- create `devices`
- create `device_bindings`
- create `device_sessions`
- create `session_transitions`
- add core indexes

### Migration 0002

- add data backfill helpers if device ownership needs to be derived from active bindings
- add extra admin-focused indexes only after real query patterns appear

## Suggested Constraints

- `devices.owner_account_id` should be nullable
- `device_bindings.unbound_at` is nullable until unbind
- `device_sessions.failure_code` is nullable unless failed or fallback path sets it
- `device_sessions.ended_at` is nullable until terminal state

## Recommendation

Do not materialize these migrations in a framework tool until the stack is confirmed. Once confirmed, translate this draft into the chosen tool's first migration file without changing the field set casually.
