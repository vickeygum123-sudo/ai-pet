# Device Session Foundation Sync Handoff

## Version

- MVP

## Task ID

- `MVP-T3 / MVP-T6 / MVP-T8` backend-owned portion only

## Current Branch

- `feat/backend-device-session-foundation`

## Can Be Synced Now

The following contracts are stable enough to sync outward for MVP parallel work:

### Frontend

- account creation payload and response
- bind API route and fields
- entitlement lookup response shape
- admin query response shapes if frontend will render admin screens later
- auth placeholder rule for development-only mocks

### Firmware

- backend failure code set
- bind flow expectations around pairing code and already-bound conflict
- session start payload fields owned by backend

### Admin

- overview counters
- device list fields and filters
- session list fields and filters
- session detail fields including transition history

## Should Not Be Synced As Final Yet

- real auth behavior
- shared types implementation detail
- PostgreSQL operational setup details
- future subscription/entitlement commercial policy

## Source Documents To Share

- [device-session-foundation-v0-freeze.md](/Users/mac/Desktop/Ai-pet/docs/backend/contracts/device-session-foundation-v0-freeze.md)
- [device-session-foundation.openapi.yaml](/Users/mac/Desktop/Ai-pet/docs/backend/contracts/device-session-foundation.openapi.yaml)
- [auth-placeholder-contract.md](/Users/mac/Desktop/Ai-pet/docs/backend/auth-placeholder-contract.md)
