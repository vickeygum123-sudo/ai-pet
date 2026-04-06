# Device Session Foundation v0 Freeze

## Version

- MVP

## Task ID

- `MVP-T3 / MVP-T6 / MVP-T8` backend-owned portion only

## Current Branch

- `feat/backend-device-session-foundation`

## Freeze Intent

This document freezes the v0 contract fields that other modules should treat as stable unless a later explicit contract update is approved.

This freeze covers only:

- failure codes
- session states
- bind API
- admin query fields
- API error response shape

This document does not freeze:

- shared types implementation
- firmware transport payload details
- frontend screen behavior
- AI orchestration internal payloads
- subscription payment policy
- real auth integration

## v0 Failure Codes

Use these values exactly:

- `AUTH_FAILED`
- `NETWORK_TIMEOUT`
- `ASR_FAILED`
- `CONTEXT_LOAD_FAILED`
- `LLM_TIMEOUT`
- `LLM_FAILED`
- `TTS_FAILED`
- `SAFETY_BLOCKED`
- `UNKNOWN_ERROR`

Source of truth:

- [device-session-foundation.openapi.yaml](/Users/mac/Desktop/Ai-pet/docs/backend/contracts/device-session-foundation.openapi.yaml#L289)
- [models.py](/Users/mac/Desktop/Ai-pet/src/backend_foundation/models.py#L45)

## v0 Session States

Use these values exactly:

- `idle`
- `listening`
- `transcribing`
- `reasoning`
- `synthesizing`
- `speaking`
- `completed`
- `failed`
- `fallback`

Source of truth:

- [device-session-foundation.openapi.yaml](/Users/mac/Desktop/Ai-pet/docs/backend/contracts/device-session-foundation.openapi.yaml#L280)
- [models.py](/Users/mac/Desktop/Ai-pet/src/backend_foundation/models.py#L26)

## v0 Bind API

### Register device

- route: `POST /v1/internal/devices`
- request fields:
  - `deviceId`
  - `hardwareModel`
  - `firmwareVersion`
  - `pairingCode`
- response fields:
  - `deviceId`
  - `hardwareModel`
  - `firmwareVersion`
  - `deviceStatus`
  - `bindStatus`
  - `ownerAccountId`
  - `pairingCode`
  - `lastOnlineAt`
  - `createdAt`

### Bind device

- route: `POST /v1/device-bindings`
- request fields:
  - `pairingCode`
- success response fields:
  - `bindingId`
  - `accountId`
  - `deviceId`
  - `status`
  - `boundAt`
  - `unboundAt`
- failure behavior:
  - `409` for already bound or invalid pairing code

### Unbind device

- route: `DELETE /v1/device-bindings/{deviceId}`
- success response:
  - `204`
- failure behavior:
  - `404` when device or active binding is not found

Source of truth:

- [device-session-foundation.openapi.yaml](/Users/mac/Desktop/Ai-pet/docs/backend/contracts/device-session-foundation.openapi.yaml#L48)

## v0 Admin Query Fields

### Overview

- route: `GET /v1/admin/overview`
- fields:
  - `totalAccounts`
  - `totalDevices`
  - `boundDevices`
  - `activeSessions`
  - `completedSessions`
  - `failedSessions`

### Device list

- route: `GET /v1/admin/devices`
- query filters:
  - `bindStatus`
  - `ownerAccountId`
- response item fields:
  - `deviceId`
  - `hardwareModel`
  - `firmwareVersion`
  - `deviceStatus`
  - `bindStatus`
  - `ownerAccountId`
  - `pairingCode`
  - `lastOnlineAt`
  - `createdAt`

### Session list

- route: `GET /v1/admin/sessions`
- query filters:
  - `state`
  - `failureCode`
  - `accountId`
  - `deviceId`
- response item fields:
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

### Session detail

- route: `GET /v1/admin/sessions/{sessionId}`
- all session list fields plus:
  - `transitions`

## Change Rule

If any of these values or fields need to change:

- open a dedicated contract update task
- update backend docs first
- notify frontend, firmware, admin, and future shared types owners before implementation diverges

## v0 API Error Response Shape

Use this response body shape for documented API errors:

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable explanation."
}
```

Stable MVP placeholder and transport-level API error codes currently documented:

- `AUTH_HEADER_REQUIRED`
- `ACCOUNT_CONFLICT`
- `DEVICE_CONFLICT`
- `BIND_TARGET_UNAVAILABLE`
- `CONFLICT`
- `NOT_FOUND`
- `VALIDATION_ERROR`
