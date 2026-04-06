# Backend + AI Minimal Integration Prep

## Version

- `0.1.0-mvp-prep`

## Current Branch

- `feat/backend-ai-minimal-integration-prep`

## Goal

- Prepare the minimum backend + AI integration surface for MVP voice-loop validation.
- Freeze only the fields and mappings needed for the first real backend/AI handshake.
- Keep this work inside the current backend freeze candidate, `MVP-T3`, `MVP-T4`, `MVP-T5`, and `MVP-T7`.

## Scope Boundary

### In scope

- align backend session fields with AI voice-loop request and response fields
- freeze the minimum contract for `failure_code`, `fallback_mode`, `safety_tags`, and latency reporting
- define the minimum integration request and response
- clarify backend-owned vs AI-owned responsibilities
- define the minimum integration test scenarios

### Out of scope

- frontend pages
- admin UI behavior
- firmware implementation
- real provider SDK integration
- shared types package landing
- production subscription and payment flows

## Inputs That Must Be Respected

- backend freeze candidate in `docs/backend/contracts/device-session-foundation-v0-freeze.md`
- `MVP-T3` voice-loop boundary
- `MVP-T4` launch persona constraints
- `MVP-T5` memory v0 rules
- `MVP-T7` safety baseline
- current AI `contracts.py`, `orchestrator.py`, and provider boundaries

## Subtasks

1. confirm the branch boundary and isolate this prep work
2. compare backend frozen session fields with AI runtime contracts
3. freeze the minimum shared field semantics
4. define the backend-to-AI request mapping
5. define the AI-to-backend response mapping
6. identify what is stable now vs what must stay open
7. define minimum contract tests and real-integration entry criteria

## Minimum Shared Identifiers

These identifiers must align exactly in the first real integration:

| Meaning | Backend field | AI field | Freeze now |
| --- | --- | --- | --- |
| request correlation | gateway-owned request id | `VoiceLoopRequest.request_id` | yes |
| user/account identity | `session.account_id` | `VoiceLoopRequest.user_id` | yes, use `account_id -> user_id` alias in MVP |
| device identity | `session.device_id` | `VoiceLoopRequest.device_id` | yes |
| session identity | `session.session_id` | `VoiceLoopRequest.session_id` | yes |
| role identity | `session.role_id` | `VoiceLoopRequest.role_id` | yes |
| locale | backend- or gateway-resolved locale | `VoiceLoopRequest.locale` | yes |

`firmware_version` remains backend-owned session metadata and is not required inside `VoiceLoopRequest` for the first integration cut.

## Minimum Integration Request

The minimum backend/gateway payload handed into AI orchestration is:

| Field | Source | Rule |
| --- | --- | --- |
| `request_id` | gateway | required for trace correlation |
| `user_id` | backend session `account_id` | required, use account id as MVP user id |
| `device_id` | backend session | required |
| `session_id` | backend session | required |
| `audio.payload` | device upload/stream | required |
| `audio.audio_format` | device metadata | required |
| `audio.sample_rate_hz` | device metadata | required |
| `audio.duration_ms` | device metadata if known | optional |
| `role_id` | backend session | optional in schema, but should always be filled from resolved session role |
| `locale` | backend/gateway | default allowed, but caller should pass the resolved locale when known |

## Minimum Integration Response

The minimum AI response that the backend/gateway must understand is:

| AI response field | Meaning | Backend action |
| --- | --- | --- |
| `session_id` | correlation key | must equal backend session id |
| `state` | terminal session outcome | map directly to backend session state |
| `transcript` | normalized ASR text | optional debug/runtime artifact only, do not freeze for persistence now |
| `response_text` | TTS source text | return to device path, not frozen for backend persistence |
| `audio_bytes` | synthesized audio | return to device path |
| `audio_format` | synthesized audio format | return to device path |
| `fallback_mode` | fallback class used | derive backend `fallback_used` |
| `failure_code` | AI runtime failure outcome | map to backend `failure_code` using the table below |
| `safety_tags` | safety category tags | derive backend `safety_flag`; raw tag persistence stays open |
| `recalled_memories` | continuity items actually injected | derive backend `continuity_recall_used` |
| `warnings` | non-blocking runtime warnings | keep in logs/notes only for MVP |
| `states_visited` | internal lifecycle trace | optional for notes/debug, not required for first live handshake |

## Field Alignment Rules

### Session state

`SessionState` is already aligned across backend and AI and can freeze now with exact value parity:

- `idle`
- `listening`
- `transcribing`
- `reasoning`
- `synthesizing`
- `speaking`
- `completed`
- `failed`
- `fallback`

### failure_code

`failure_code` cannot freeze as one identical enum across backend and AI yet. What can freeze now is the mapping rule between AI runtime failures and backend persisted failures.

| AI runtime failure code | Backend persisted failure code | Freeze now |
| --- | --- | --- |
| `none` | `null` | yes |
| `asr_failed` | `ASR_FAILED` | yes |
| `memory_read_failed` | `null` | yes, warning only in MVP because `MVP-T5` says memory read failure must not block the session |
| `safety_blocked_input` | `SAFETY_BLOCKED` | yes |
| `safety_blocked_output` | `SAFETY_BLOCKED` | yes |
| `llm_failed` | `LLM_FAILED` | yes |
| `tts_failed` | `TTS_FAILED` | yes |

Backend-only failure codes that remain outside the current AI response contract:

- `AUTH_FAILED`
- `NETWORK_TIMEOUT`
- `CONTEXT_LOAD_FAILED`
- `LLM_TIMEOUT`
- `UNKNOWN_ERROR`

These stay backend or gateway owned until a later contract update decides whether AI should emit them directly.

### fallback_mode

`fallback_mode` is AI-owned and can freeze now as the runtime classification returned to backend/gateway:

- `none`
- `soft_redirect`
- `firm_refusal`
- `supportive_risk_response`
- `technical_recovery`

Backend v0 does not need to persist the exact fallback mode yet. For MVP first integration:

- `fallback_used = false` when `fallback_mode = none`
- `fallback_used = true` for every other `fallback_mode`

If admin later needs exact fallback breakdowns, add a dedicated contract update instead of overloading `failure_code`.

### safety_tags

The raw tag array is AI-owned. For the first integration cut, freeze only the current minimum stable tag vocabulary that already matches the implemented mock safety path:

- `self_harm`
- `violence`
- `illegal_guidance`
- `dependency_risk`

Backend v0 integration rules:

- `safety_flag = true` when `safety_tags` is non-empty
- `safety_flag = true` when mapped backend `failure_code = SAFETY_BLOCKED`
- raw tag persistence is not frozen in backend schema yet

Safety categories from `MVP-T7` that are product-level requirements but are not frozen as runtime tag values yet:

- sexual content
- youth-sensitive content
- privacy overreach
- richer emotional dependency variants beyond `dependency_risk`

### latency

Latency needs a split freeze, not a single shared payload freeze.

Freeze now:

| Metric | Owner | Meaning |
| --- | --- | --- |
| `first_response_latency_ms` | backend persisted field | elapsed time from end of user speech to first playable AI audio returned toward device |
| `asr` | AI internal metric | ASR stage duration |
| `context_assembly` | AI internal metric | persona + entitlement + memory recall build time |
| `llm_first_token` | AI internal metric | generation wait until first text output |
| `safety_total` | AI internal metric | combined input and output safety time |
| `tts_first_chunk` | AI internal metric | TTS time to first audio output |
| `end_to_first_audio` | AI budget name | same user-facing metric family as backend `first_response_latency_ms` |

Do not freeze yet:

- a serialized `latency` object inside `VoiceLoopResponse`
- per-stage latency persistence in backend session schema
- admin filtering or aggregation by AI stage latency

For the first real integration, backend only needs `first_response_latency_ms`. AI stage latency breakdown can remain log-only.

## VoiceLoop <-> Backend Session Mapping

### Request mapping

| Backend source | VoiceLoop field | Note |
| --- | --- | --- |
| `session.session_id` | `session_id` | exact copy |
| `session.account_id` | `user_id` | identity alias for MVP |
| `session.device_id` | `device_id` | exact copy |
| `session.role_id` | `role_id` | exact copy |
| session locale resolution | `locale` | default allowed |
| gateway trace id | `request_id` | generated per request |
| device audio payload | `audio.*` | transport-owned, then passed through |

### Response mapping into backend session update

| VoiceLoop response | Backend update field | Mapping rule |
| --- | --- | --- |
| `state` | `state` | direct |
| `failure_code` | `failure_code` | use AI-to-backend mapping table |
| `fallback_mode` | `fallback_used` | `true` when not `none` |
| `safety_tags` | `safety_flag` | `true` when non-empty |
| `recalled_memories` | `continuity_recall_used` | `true` when non-empty |
| `transcript` present and no ASR failure | `asr_status` | `succeeded` |
| `failure_code = asr_failed` | `asr_status` | `failed` |
| `failure_code in {llm_failed, safety_blocked_input}` | `llm_status` | `failed` for `llm_failed`, `skipped` for `safety_blocked_input` |
| `failure_code = safety_blocked_output` | `llm_status` | `succeeded` because generation happened; output was replaced later |
| `audio_bytes` present | `tts_status` | `succeeded` |
| `failure_code = tts_failed` or `audio_bytes is null` | `tts_status` | `failed` |
| measured first audio latency | `first_response_latency_ms` | set when gateway can measure it |
| `warnings` and optional mapping notes | `notes` | free-text only, not schema-stable |

## Responsibility Split

### Backend owns

- device/account/session source of truth
- bind and session APIs
- resolved `role_id` and entitlement snapshot at session start
- persisted `state`, `failure_code`, `first_response_latency_ms`, and admin query projections
- gateway and auth failures outside AI runtime

### AI owns

- ASR, memory recall, prompt build, safety chain, LLM, TTS
- `fallback_mode`
- `safety_tags`
- `warnings`
- recalled memory selection
- runtime stage latency measurements

### Integration layer owns

- building `VoiceLoopRequest` from backend session plus device audio
- translating `VoiceLoopResponse` into backend session update fields
- measuring and setting `first_response_latency_ms`
- preserving enough logs to debug unmapped warnings without expanding contracts too early

## What Can Freeze Now

- shared session state values
- MVP identity alias rule: backend `account_id` maps to AI `user_id`
- minimum `VoiceLoopRequest` field list
- minimum `VoiceLoopResponse` field list
- AI-to-backend `failure_code` mapping table
- `fallback_mode` exact runtime values
- minimum stable `safety_tags` vocabulary currently implemented
- backend `first_response_latency_ms` meaning

## What Must Stay Open

- whether backend and AI will share one final `FailureCode` enum
- whether `memory_read_failed` should later persist as a dedicated backend code
- raw safety tag persistence schema
- final tag taxonomy for sexual, youth-sensitive, and privacy categories
- serialized per-stage latency payloads
- transcript persistence policy
- provider/model identifiers in persisted session records
- shared types package design

## Minimum Integration Test Scenarios

1. Happy path
   Backend creates a session, AI returns `completed`, no fallback, no safety tags, memory recall may be present, and backend records success plus latency.
2. Memory recall degraded but non-blocking
   AI returns `completed` with warning `memory_read_failed`, backend keeps `failure_code = null`, and the session still counts as successful.
3. Input safety block
   AI returns `fallback` with `safety_blocked_input`, `supportive_risk_response` or `firm_refusal`, and backend records `SAFETY_BLOCKED`, `safety_flag = true`, `fallback_used = true`.
4. Output safety rewrite
   AI returns `fallback` with `safety_blocked_output`, non-empty `safety_tags`, backend records `SAFETY_BLOCKED`, and `llm_status` remains `succeeded`.
5. LLM technical fallback
   AI returns `fallback` with `llm_failed`, backend records `LLM_FAILED`, `fallback_used = true`, and session stays reviewable.
6. TTS failure after text generation
   AI returns `failed` with `tts_failed`, backend records `TTS_FAILED`, `tts_status = failed`, and no silent success is allowed.

## Risks

- backend and AI currently use different `FailureCode` enum shapes; treating them as identical would create false contract stability
- `user_id` vs `account_id` is only an MVP alias and will need revisiting before broader identity work
- `dependency_risk` is the current runtime tag, while product language is broader emotional dependency; docs must not treat that as the full long-term taxonomy
- backend schema cannot yet persist raw `fallback_mode` or raw `safety_tags`, which limits admin detail during early pilots
- AI stage latency is budgeted, but only first-response latency is persistable today

## Test And Validation

- add contract tests that enforce shared session state parity
- add contract tests that enforce the AI-to-backend failure mapping table
- add contract tests that guard the currently frozen fallback and safety tag vocabulary
- run backend foundation tests, AI voice-loop tests, and the new alignment tests together before real integration

## Readiness Decision

### Suitable for next real integration step

- yes, if the gateway or integration layer uses the mapping rules in this document and does not assume backend and AI enums are identical

### Suitable to merge directly to `main`

- not yet recommended as a final product contract if the backend freeze candidate and AI orchestrator candidate are still under review
- acceptable to merge after review as a prep and alignment artifact, but it should land together with the mapping tests in the same review packet

## Special Reminder For Control

- do not ask backend or AI teams to "just unify enums in code" before the ownership split is accepted
- first real integration should be one thin translator layer, not a shared-types refactor
- if admin needs exact `fallback_mode`, raw `safety_tags`, or stage latency persistence, open a dedicated contract task after the first live handshake is proven
