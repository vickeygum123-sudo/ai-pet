# MVP Execution Entrypoint

## 1. Planning Status

The MVP planning phase is complete enough to begin implementation work.

Completed planning tasks:

- `MVP-T1` launch user and value proposition
- `MVP-T2` core scenarios and success metrics
- `MVP-T3` voice loop v0
- `MVP-T4` launch persona card v0
- `MVP-T5` memory v0
- `MVP-T6` account, bind, and setup flow
- `MVP-T7` safety baseline
- `MVP-T8` observability v0

## 2. First Implementation Workstreams

These should be split into separate topic dialogues and separate branches.

### Workstream A: firmware connectivity and audio path

- primary module: firmware
- goal: power-on, Wi-Fi setup, cloud connection, audio capture, audio playback, device state
- suggested branch: `feat/firmware-audio-connect-v0`

### Workstream B: backend device/account/session foundation

- primary module: backend
- goal: device identity, bind flow, session records, entitlement lookup, basic admin query APIs
- suggested branch: `feat/backend-device-session-foundation`

### Workstream C: AI orchestration loop

- primary module: AI orchestration
- goal: ASR -> context -> safety -> LLM -> safety -> TTS loop with fallback
- suggested branch: `feat/ai-voice-loop-v0`

### Workstream D: onboarding web

- primary module: frontend
- goal: account creation, setup flow, Wi-Fi guidance, bind success, device page
- suggested branch: `feat/web-onboarding-bind-flow`

### Workstream E: admin observability

- primary module: admin
- goal: overview dashboard, session list/detail, failure view, review queue
- suggested branch: `feat/admin-observability-v0`

## 3. Execution Order

Recommended order:

1. Backend device/account/session foundation
2. AI orchestration loop
3. Firmware connectivity and audio path
4. Onboarding web
5. Admin observability

Reason:

- backend and AI contracts must exist before frontend and firmware can integrate cleanly
- firmware and web should implement against stable ownership and session contracts
- admin observability depends on event and state definitions from the other workstreams

## 4. Cross-Module Split Rules During Execution

- Do not mix firmware work and AI orchestration work in one implementation branch.
- Do not mix backend bind/session work with subscription implementation.
- Do not mix observability screens with persona prompt tuning.
- If a task touches more than one module, first produce an interface contract and then split execution branches.

## 5. MVP Implementation Done Definition

The MVP implementation is ready for pilot when:

- a user can bind a device and complete a first conversation
- the companion role feels recognizable and safe
- recent continuity works in repeat sessions
- the team can inspect failures and risky sessions
- latency and success rate are good enough to support short daily use

## 6. Next Dialogue Recommendations

- Topic 1: backend implementation breakdown from `MVP-T3`, `MVP-T6`, and `MVP-T8`
- Topic 2: AI orchestration implementation breakdown from `MVP-T3`, `MVP-T4`, `MVP-T5`, and `MVP-T7`
- Topic 3: firmware implementation breakdown from `MVP-T3` and `MVP-T6`

## 7. Merge Guidance

- This planning branch can merge to `main` once reviewed because it is documentation-only.
- Start implementation only in new branches scoped to one workstream each.
