# Device Session Foundation Freeze Review Checklist

## Version

- MVP

## Task ID

- `MVP-T3 / MVP-T6 / MVP-T8` backend-owned portion only

## Current Branch

- `feat/backend-device-session-foundation`

## Review Status

- candidate freeze for MVP backend baseline
- approved for parallel contract review
- not approved yet for merge to `main`

## This Review Should Freeze

### Interfaces

- `POST /v1/accounts`
- `GET /v1/accounts/me`
- `POST /v1/internal/devices`
- `POST /v1/device-bindings`
- `DELETE /v1/device-bindings/{deviceId}`
- `GET /v1/entitlements/me`
- `POST /v1/device-sessions`
- `PATCH /v1/device-sessions/{sessionId}`
- `GET /v1/admin/overview`
- `GET /v1/admin/devices`
- `GET /v1/admin/sessions`
- `GET /v1/admin/sessions/{sessionId}`

Primary source:

- [device-session-foundation.openapi.yaml](/Users/mac/Desktop/Ai-pet/docs/backend/contracts/device-session-foundation.openapi.yaml)

### Fields

#### Account

- `accountId`
- `authSubject`
- `displayName`
- `defaultRoleId`
- `entitlementTier`
- `createdAt`

#### Device

- `deviceId`
- `hardwareModel`
- `firmwareVersion`
- `deviceStatus`
- `bindStatus`
- `ownerAccountId`
- `pairingCode`
- `lastOnlineAt`
- `createdAt`

#### Binding

- `bindingId`
- `accountId`
- `deviceId`
- `status`
- `boundAt`
- `unboundAt`

#### Entitlement

- `accountId`
- `tier`
- `features.voiceSession`
- `features.recentContinuityMemory`
- `features.priorityGeneration`

#### Session

- `sessionId`
- `accountId`
- `deviceId`
- `roleId`
- `entitlementTier`
- `state`
- `asrStatus`
- `llmStatus`
- `ttsStatus`
- `safetyFlag`
- `fallbackUsed`
- `continuityRecallUsed`
- `firstResponseLatencyMs`
- `failureCode`
- `firmwareVersion`
- `startedAt`
- `endedAt`
- `transitions`

#### Admin Overview

- `totalAccounts`
- `totalDevices`
- `boundDevices`
- `activeSessions`
- `completedSessions`
- `failedSessions`

#### Admin Query Filters

- device list:
  - `bindStatus`
  - `ownerAccountId`
- session list:
  - `state`
  - `failureCode`
  - `accountId`
  - `deviceId`

Primary sources:

- [device-session-foundation-v0-freeze.md](/Users/mac/Desktop/Ai-pet/docs/backend/contracts/device-session-foundation-v0-freeze.md)
- [device-session-foundation-sync-handoff.md](/Users/mac/Desktop/Ai-pet/docs/backend/contracts/device-session-foundation-sync-handoff.md)

### Failure Codes

- `AUTH_FAILED`
- `NETWORK_TIMEOUT`
- `ASR_FAILED`
- `CONTEXT_LOAD_FAILED`
- `LLM_TIMEOUT`
- `LLM_FAILED`
- `TTS_FAILED`
- `SAFETY_BLOCKED`
- `UNKNOWN_ERROR`

### Session States

- `idle`
- `listening`
- `transcribing`
- `reasoning`
- `synthesizing`
- `speaking`
- `completed`
- `failed`
- `fallback`

## This Review Also Freezes

### API Error Response Shape

All documented API errors should use:

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable explanation."
}
```

Current documented transport and placeholder error codes:

- `AUTH_HEADER_REQUIRED`
- `ACCOUNT_CONFLICT`
- `DEVICE_CONFLICT`
- `BIND_TARGET_UNAVAILABLE`
- `CONFLICT`
- `NOT_FOUND`
- `VALIDATION_ERROR`

### Auth Placeholder Contract

The following is frozen only as a development placeholder:

- header: `X-Account-Id`
- applies to:
  - `GET /v1/accounts/me`
  - `POST /v1/device-bindings`
  - `DELETE /v1/device-bindings/{deviceId}`
  - `GET /v1/entitlements/me`

Source:

- [auth-placeholder-contract.md](/Users/mac/Desktop/Ai-pet/docs/backend/auth-placeholder-contract.md)

## Still Not Frozen

- real auth integration
- device authentication implementation
- shared types package shape
- frontend form behavior and page flow
- firmware transport payload implementation details
- AI orchestration request/response internals
- subscription payment and formal entitlement business policy
- PostgreSQL runtime readiness
- deployment, secrets, backup, and operational infra conventions

## If Other Modules Start Integrating Now

### Frontend

- use the documented route paths and camelCase field names exactly
- treat `X-Account-Id` as a temporary dev-only placeholder, not a productized auth design
- do not infer payment or subscription screens from current entitlement flags

### Firmware

- treat backend failure codes as stable log and support codes
- do not assume persona, memory, or AI internals from the session API
- bind flow should treat invalid pairing code and already-bound device as backend-controlled outcomes

### Admin

- build against the frozen overview, list, filter, and detail fields
- do not add extra derived fields to the shared contract without a contract update task

### All Modules

- if a field rename or enum change seems necessary, stop and open a dedicated contract update task first
- do not bypass the freeze doc by copying local assumptions into code

## Review Questions

- are all route paths acceptable as the MVP baseline
- are the current field names acceptable for cross-module use
- are the failure codes sufficient for backend, firmware, and admin visibility
- are the session states sufficient for runtime and review use
- is the placeholder auth approach clearly temporary and non-blocking for other modules

## Recommended Review Outcome Labels

- `freeze-approved`
- `freeze-approved-with-follow-up`
- `freeze-blocked`
