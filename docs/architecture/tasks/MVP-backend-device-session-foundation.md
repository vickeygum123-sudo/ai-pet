# MVP Backend Device Session Foundation

## Task Metadata

| Field | Value |
| --- | --- |
| Version | MVP |
| Task ID | MVP-T3 / MVP-T6 / MVP-T8 |
| Coverage note | Partial coverage of the backend-owned portions only |
| Topic module | Backend |
| Current branch | `feat/backend-device-session-foundation` |
| Goal | Establish the backend source of truth for account, device, bind, session, entitlement lookup, and basic admin query APIs |
| Out of scope | Subscription payment, frontend pages, AI prompt logic, firmware implementation |
| Cross-module status | Backend-only implementation; contract outputs require follow-up sync with frontend, firmware, admin, and shared types if adopted |
| Merge guidance | Do not merge to `main` yet; continue until runtime framework and shared contracts are confirmed |

## Task Goal

Turn the MVP planning outputs from `MVP-T3`, `MVP-T6`, and `MVP-T8` into a backend foundation that other modules can integrate against without mixing in billing, AI prompt work, or firmware behavior.

This foundation should give the project:

- a stable backend domain model
- a stable failure code and session state set
- a first-pass API contract for onboarding, bind, session, entitlement, and admin queries
- a minimal executable service skeleton to prove the core rules

## This Iteration Boundary

### In scope

- account source-of-truth model
- device registration and ownership model
- bind and unbind rules
- session lifecycle persistence model
- basic entitlement lookup shape
- admin overview, device list, session list, and session detail query shape
- backend failure taxonomy shared outward as a contract

### Out of scope

- payment provider integration
- subscription lifecycle state machine
- onboarding UI implementation
- device transport or audio streaming protocol
- AI orchestration internals such as ASR, LLM, TTS, prompt assembly, or safety inference
- firmware-side pairing implementation

## Split Subtasks

### B1. Backend domain model

- define account, device, binding record, session, entitlement snapshot, and admin summary objects
- define states, failure codes, and minimal ownership rules

### B2. Bind and ownership contract

- define device registration inputs
- define bind and unbind API contract
- define duplicate bind and already-bound failure behavior

### B3. Session and entitlement contract

- define session start and update payloads
- define session lifecycle fields needed by backend, AI orchestration, and admin
- define the basic entitlement response consumed by runtime services

### B4. Admin query contract

- define overview, device list, session list, and session detail query/response shapes
- make sure the filter set aligns with `MVP-T3` and `MVP-T8`

### B5. Executable backend skeleton

- implement a framework-agnostic service layer that enforces the core rules in memory
- cover bind, entitlement, session lifecycle, and admin queries with tests

## Modules Involved

- backend domain and service layer
- backend API contract docs
- backend admin query contract docs

### Follow-up modules to sync later

- frontend onboarding flow
- firmware error code mapping and bind protocol
- AI orchestration session ingestion and entitlement lookup
- admin UI data bindings
- shared types package if a shared contract layer is introduced

## Planned Changes

- add a backend foundation task document
- add a backend OpenAPI contract draft
- add a backend data model document
- add a minimal Python service skeleton for backend rules
- add tests that prove the foundation behavior

## Dependencies

- `MVP-T3` session states, failure codes, and observability slices
- `MVP-T6` bind flow, ownership model, and setup errors
- `MVP-T8` admin overview and session detail requirements

## Risks

- the repository does not yet show a chosen backend runtime framework, so the implementation is intentionally framework-agnostic
- API route shapes may need adjustment once frontend and firmware integration starts
- failure codes and state enums should move into shared types before cross-module implementation begins
- entitlement flags are intentionally minimal and may change when formal subscription policy is designed
- session fields may expand after AI orchestration confirms latency stamps and safety tags

## Outputs

- [MVP-backend-device-session-foundation.md](/Users/mac/Desktop/Ai-pet/docs/architecture/tasks/MVP-backend-device-session-foundation.md)
- [device-session-foundation.openapi.yaml](/Users/mac/Desktop/Ai-pet/docs/backend/contracts/device-session-foundation.openapi.yaml)
- [device-session-foundation-data-model.md](/Users/mac/Desktop/Ai-pet/docs/backend/contracts/device-session-foundation-data-model.md)
- [models.py](/Users/mac/Desktop/Ai-pet/src/backend_foundation/models.py)
- [service.py](/Users/mac/Desktop/Ai-pet/src/backend_foundation/service.py)
- [test_backend_foundation.py](/Users/mac/Desktop/Ai-pet/tests/test_backend_foundation.py)

## Acceptance Criteria

- backend ownership boundaries remain inside account, device, bind, session, entitlement lookup, and admin query scope
- API contract is concrete enough for frontend, firmware, AI orchestration, and admin follow-up work
- the service skeleton enforces already-bound, bind, unbind, session start, session completion, and session failure rules
- admin query outputs expose overview metrics and session filtering fields required by MVP planning docs
- tests cover the main happy path plus at least one failure path

## Test And Validation Plan

- run unit tests for bind, entitlement, session lifecycle, and admin query logic
- manually inspect the OpenAPI contract against `MVP-T3`, `MVP-T6`, and `MVP-T8`
- confirm no AI, firmware, payment, or frontend implementation files were changed

## Recommendation To Control Owner

- keep this branch focused on backend foundation only
- do not start frontend or firmware integration in this branch
- sync shared failure codes and enum names before parallel implementation begins
- decide backend runtime framework soon so this foundation can be wired into a real service without contract drift
