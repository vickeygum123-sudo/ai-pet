# MVP-T8 Build Observability v0

## Task Metadata

| Field | Value |
| --- | --- |
| Task ID | MVP-T8 |
| Title | Build observability v0 |
| Primary module | Admin |
| Related modules | Backend, AI Orchestration, Firmware, Safety |
| Type | execution |
| Priority | P1 |
| Branch suggestion | `docs/mvp-t8-observability-v0` |
| Merge rule | Documentation-only, can merge to `main` after review |
| Status | done |

## 1. Goal

- Give the team enough visibility to understand whether the MVP is working, failing, safe, and worth iterating.
- Make session quality, device health, and safety review visible without building a heavy BI platform.

## 2. MVP Dashboard Scope

### Device health view

- online devices
- last online time
- firmware version distribution
- setup failures by step

### Session quality view

- sessions started
- sessions completed
- session success rate
- median first-response latency
- ASR, LLM, and TTS latency slices
- failure count by code

### Continuity view

- continuity recall attempts
- continuity recalls used
- repeat-user sessions
- reviewed "felt remembered" tags

### Safety view

- flagged sensitive sessions
- fallback trigger counts
- blocked outputs
- review queue size

## 3. Minimum Admin Pages

- overview dashboard
- device list
- session list
- session detail
- failure breakdown
- review queue

## 4. Session Detail Requirements

Each inspectable session should include:

- session id
- device id
- user id
- role id
- entitlement tier
- timestamps
- state transitions
- latency breakdown
- failure code if present
- continuity recall used or not
- safety tags
- fallback triggered or not

## 5. Required Logging and Event Alignment

Observability should align with `MVP-T2` metric definitions and `MVP-T3` state/failure definitions.

Minimum alignment points:

- bind funnel events
- session lifecycle events
- latency timestamps
- safety tags
- continuity recall events
- firmware version context

## 6. Alerting Priorities

MVP alerting should be simple and focused.

- session success rate drops sharply
- median first-response latency crosses threshold
- one failure code spikes
- safety fallback rate spikes unusually
- setup completion drops sharply after a firmware or backend change

## 7. Ownership Split

### Backend

- event ingestion
- session metadata persistence
- query APIs

### Admin

- dashboards
- filters
- review UI

### AI Orchestration

- latency stamps
- safety and continuity tags
- model outcome logging

### Firmware

- firmware version reporting
- device-state reporting

## 8. Acceptance

- The team can answer whether a failed experience is caused by setup, transport, ASR, LLM, TTS, or safety intervention.
- The team can inspect continuity and safety quality during pilots.
- The dashboard scope is small enough to implement quickly.

## 9. Recommended Next Tasks

- Backend topic: event schema and query endpoints.
- Admin topic: overview and session-detail screens.
- AI topic: latency and safety tagging instrumentation.
