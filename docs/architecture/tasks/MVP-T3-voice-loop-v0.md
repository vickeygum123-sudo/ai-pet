# MVP-T3 Define Voice Loop v0

## Task Metadata

| Field | Value |
| --- | --- |
| Task ID | MVP-T3 |
| Title | Define voice loop v0 |
| Primary module | AI Orchestration |
| Related modules | Backend, Firmware, Safety, Admin |
| Type | architecture |
| Priority | P0 |
| Branch suggestion | `docs/mvp-t3-voice-loop-v0` |
| Merge rule | Documentation-only, can merge to `main` after review |
| Status | done |

## 1. Goal

- Define the MVP end-to-end speech-to-dialogue-to-speech path.
- Keep the hardware lightweight and move orchestration to the cloud.
- Ensure the system is good enough for short, frequent, emotionally warm conversations.
- Make ownership boundaries clear across firmware, backend, AI orchestration, and safety.

## 2. Design Principles

- Device is an entry point, not the intelligence center.
- Minimize on-device logic beyond capture, playback, connectivity, and fail-safe behavior.
- Optimize for low-friction conversational flow, not broad assistant capability.
- Keep memory lightweight and recent-continuity-focused for MVP.
- Fail safely when any part of the cloud pipeline degrades.

## 3. MVP Voice Loop Scope

### In scope

- Wi-Fi-connected device sends user speech to cloud.
- Cloud performs ASR, dialogue orchestration, safety checks, memory injection, LLM generation, TTS generation, and audio return.
- Device plays returned audio and updates local state.
- Backend stores session metadata and limited continuity artifacts.
- Admin can inspect key failures and core latency metrics.

### Out of scope

- Fully offline dialogue.
- On-device large-model inference.
- Multi-turn barge-in refinement beyond MVP-level interruption handling.
- Multi-device session continuity.
- Complex tool use and external action execution.

## 4. High-Level Flow

### End-to-end sequence

1. User activates device and starts speaking.
2. Firmware captures audio and streams or uploads it to the cloud gateway.
3. Gateway authenticates device and creates or resumes a conversation session.
4. AI orchestration sends audio to ASR.
5. ASR result is normalized and passed into dialogue orchestration.
6. Dialogue orchestration loads:
   - role card
   - recent continuity memory
   - entitlement tier
   - safety policy
7. Safety pre-check runs on user utterance and dialogue context.
8. LLM prompt is composed and generation is executed.
9. Safety post-check runs on generated text.
10. Safe response text is sent to TTS.
11. TTS audio is streamed or returned to firmware.
12. Firmware plays audio and marks session response completion.
13. Backend records session metadata, failure state, and continuity updates.

## 5. Module Responsibility Split

## Firmware

### Owns

- Device boot and Wi-Fi state.
- Audio capture and playback.
- Device authentication token attachment.
- Basic local user state such as listening, thinking, speaking, and error indicator.
- Retry behavior within simple network/connectivity limits.

### Does not own

- Persona logic.
- Long-term memory decisions.
- Subscription logic.
- Sensitive topic reasoning.

## Backend

### Owns

- Device identity and account/device binding.
- Session creation and metadata persistence.
- Role assignment lookup.
- Entitlement lookup.
- Admin-facing data query APIs.

### Does not own

- Core prompt composition.
- Model routing as the primary runtime brain.

## AI Orchestration

### Owns

- ASR integration.
- Context assembly.
- Memory recall injection.
- Persona enforcement.
- Safety checks in the generation path.
- LLM and TTS execution path.
- Dialogue fallback behavior.

### Does not own

- Device transport implementation.
- Billing source of truth.

## Safety Layer

### Owns

- Sensitive topic classification.
- Unsafe output interception.
- Fallback policy.
- Review signals and escalation tags.

### Does not own

- Generic product analytics.
- Device connectivity recovery.

## Admin

### Owns

- Visibility into session funnel and failures.
- Latency and stability dashboards.
- Safety review sampling hooks.

## 6. Recommended Runtime Topology

### Minimal cloud services

- `device-gateway`
  - receives device audio requests
  - validates device identity
  - opens session
- `conversation-orchestrator`
  - drives ASR -> memory -> safety -> LLM -> safety -> TTS
- `session-service`
  - stores session records and response outcomes
- `memory-service`
  - returns recent continuity context and stores new continuity artifacts
- `persona-service`
  - returns role card and configurable persona parameters
- `entitlement-service`
  - returns free/subscription capability flags
- `admin-api`
  - exposes operational data and review views

These can be implemented as separate services or as modular components inside one backend in MVP. The key requirement is boundary clarity, not microservice count.

## 7. Conversation State Model

### Session states

- `idle`
- `listening`
- `transcribing`
- `reasoning`
- `synthesizing`
- `speaking`
- `completed`
- `failed`
- `fallback`

### Minimum persisted session data

- session id
- user id
- device id
- role id
- entitlement tier
- start time
- end time
- ASR status
- LLM status
- TTS status
- safety flag
- failure code
- continuity recall used or not

## 8. Latency Budget

For MVP companionship use, response speed should feel conversational even if not instant.

| Stage | Recommended budget |
| --- | --- |
| Device upload / stream start | <= 300ms added overhead |
| ASR | <= 700ms for short utterances |
| Context assembly + memory fetch | <= 250ms |
| LLM first text output | <= 900ms |
| Safety checks | <= 150ms total target |
| TTS first audio chunk | <= 500ms |
| End-of-user-speech to first audio response | <= 2.5s median target |

If this budget cannot be met consistently, the system should prefer shorter responses and smaller context over heavier memory recall in MVP.

## 9. Safety and Fallback Path

### Pre-generation safety

- Detect self-harm, violence, sexual content risk, illegal content, and youth-sensitive risk.
- Tag the session for stricter response rules when needed.

### Post-generation safety

- Block unsafe generated content before TTS.
- Replace with approved fallback text when needed.

### Fallback classes

- `network_failure_fallback`
- `asr_failure_fallback`
- `generation_timeout_fallback`
- `unsafe_content_fallback`
- `unknown_error_fallback`

### MVP fallback rule

- The device should always return a polite and in-character recovery line where safe to do so.
- Hard silent failures should be treated as a product defect, not an acceptable UX path.

## 10. Memory Usage in Voice Loop v0

- Only recent continuity memory should be injected.
- Memory recall should be limited to high-confidence, recent, relevant items.
- If memory fetch fails, the dialogue should continue without memory rather than block the session.
- Memory write-back should be asynchronous where possible to avoid stretching response latency.

## 11. Firmware-Cloud Contract v0

### Firmware sends

- device auth token
- firmware version
- device id
- audio payload or audio stream
- client timestamp
- optional local state flags

### Cloud returns

- session id
- response audio payload or stream
- response metadata:
  - role id
  - fallback used or not
  - error code if present
  - server timestamp

### Contract principles

- Firmware should not need to understand persona or memory internals.
- Cloud should not assume perfect connectivity.
- All failures returned to firmware should map to a small, stable error code set.

## 12. Failure Taxonomy

Use a compact failure code set in MVP:

- `AUTH_FAILED`
- `NETWORK_TIMEOUT`
- `ASR_FAILED`
- `CONTEXT_LOAD_FAILED`
- `LLM_TIMEOUT`
- `LLM_FAILED`
- `TTS_FAILED`
- `SAFETY_BLOCKED`
- `UNKNOWN_ERROR`

This code set should be shared by firmware, backend logs, and admin views.

## 13. Observability Requirements

The system should expose at least:

- session start count
- session success count
- failure count by code
- median first-response latency
- ASR latency
- LLM latency
- TTS latency
- continuity recall attempt rate
- continuity recall use rate
- safety fallback trigger count

Admin review should allow slicing by:

- firmware version
- role id
- entitlement tier
- network outcome
- failure code

## 14. Acceptance

- Responsibilities are clear enough that firmware, backend, and AI work can split cleanly.
- End-to-end path is narrow enough for MVP and does not drift into general assistant complexity.
- Latency target is explicit enough to guide implementation trade-offs.
- Failure and safety paths are defined well enough for observability and review.

## 15. Recommended Next Tasks

- `MVP-T4`: define launch persona card and expression rules.
- `MVP-T5`: define memory v0 schema and recall policy.
- `MVP-T6`: define account, bind, and setup flow using this contract.
- `MVP-T8`: design admin observability around these states, codes, and metrics.
