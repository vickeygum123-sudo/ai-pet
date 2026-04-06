# Device Session Foundation Data Model

## Scope

This model covers only the MVP backend foundation for:

- account
- device
- binding
- session
- entitlement snapshot
- admin query projections

It does not define payment transactions, persona prompt content, memory payload bodies, or firmware transport internals.

## Entity Summary

### Account

| Field | Type | Notes |
| --- | --- | --- |
| `account_id` | string | Primary identifier |
| `auth_subject` | string | External auth provider subject |
| `display_name` | string nullable | User-facing name |
| `default_role_id` | string | Launch role reference only, not persona definition |
| `entitlement_tier` | enum | `free` or `subscribed` in this MVP foundation |
| `created_at` | datetime | Audit timestamp |

### Device

| Field | Type | Notes |
| --- | --- | --- |
| `device_id` | string | Primary identifier |
| `hardware_model` | string | Hardware SKU/model |
| `firmware_version` | string | Last reported firmware version |
| `device_status` | enum | `pairing_ready`, `connecting`, `connected`, `failed_to_connect`, `ready_to_speak`, `offline` |
| `bind_status` | enum | `unbound` or `bound` |
| `owner_account_id` | string nullable | Current owner |
| `pairing_code` | string | Short-lived code shown during setup |
| `created_at` | datetime | Registration timestamp |
| `last_online_at` | datetime nullable | Last heartbeat |

### Binding Record

| Field | Type | Notes |
| --- | --- | --- |
| `binding_id` | string | Primary identifier |
| `account_id` | string | Owner account |
| `device_id` | string | Bound device |
| `status` | enum | `bound` or `unbound` |
| `bound_at` | datetime | Bind time |
| `unbound_at` | datetime nullable | Unbind time |

### Session

| Field | Type | Notes |
| --- | --- | --- |
| `session_id` | string | Primary identifier |
| `account_id` | string | Session owner |
| `device_id` | string | Source device |
| `role_id` | string | Resolved role identifier only |
| `entitlement_tier` | enum | Snapshot at session start |
| `state` | enum | `idle`, `listening`, `transcribing`, `reasoning`, `synthesizing`, `speaking`, `completed`, `failed`, `fallback` |
| `asr_status` | enum | `pending`, `succeeded`, `failed`, `skipped` |
| `llm_status` | enum | `pending`, `succeeded`, `failed`, `skipped` |
| `tts_status` | enum | `pending`, `succeeded`, `failed`, `skipped` |
| `safety_flag` | bool | Session tagged by safety checks or fallback |
| `fallback_used` | bool | Whether a recovery line was used |
| `failure_code` | enum nullable | Shared error taxonomy |
| `continuity_recall_used` | bool | Recent continuity used or not |
| `first_response_latency_ms` | integer nullable | First response latency |
| `firmware_version` | string | Firmware reported at start |
| `started_at` | datetime | Session start |
| `ended_at` | datetime nullable | Session end |

### Session Transition

| Field | Type | Notes |
| --- | --- | --- |
| `session_id` | string | Parent session |
| `state` | enum | Lifecycle state reached |
| `recorded_at` | datetime | Transition time |
| `notes` | string nullable | Optional internal annotation |

## Shared Enums

### Entitlement tiers

- `free`
- `subscribed`

### Failure codes

- `AUTH_FAILED`
- `NETWORK_TIMEOUT`
- `ASR_FAILED`
- `CONTEXT_LOAD_FAILED`
- `LLM_TIMEOUT`
- `LLM_FAILED`
- `TTS_FAILED`
- `SAFETY_BLOCKED`
- `UNKNOWN_ERROR`

## Ownership Rules

- one device can have only one active owner at a time
- a bind request must target a known device pairing code
- unbind closes the active binding record and clears `owner_account_id`
- a session can start only when the device exists and is actively bound to the requesting account
- session entitlement is copied from the account at session start so later account changes do not rewrite history

## Admin Query Projections

### Overview projection

- total accounts
- total devices
- bound devices
- active sessions
- completed sessions
- failed sessions

### Device list projection

- device id
- hardware model
- firmware version
- device status
- bind status
- owner account id
- last online at

### Session list projection

- session id
- account id
- device id
- role id
- entitlement tier
- state
- failure code
- safety flag
- fallback used
- first response latency
- started at
- ended at

### Session detail projection

- all session list fields
- ASR, LLM, TTS status
- continuity recall used
- transition history

## Suggested Persistence Notes

- model these entities in a relational database for MVP operational clarity
- index `device.owner_account_id`, `device.last_online_at`, `session.started_at`, `session.failure_code`, and `binding.account_id`
- keep failure codes and state enums synchronized with firmware logs and admin filters through shared types as soon as that package exists
