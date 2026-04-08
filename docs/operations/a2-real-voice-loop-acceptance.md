# A2 Real Voice Loop Acceptance

## Document Status

- Review mode only
- No new feature expansion
- Last updated: 2026-04-06

## Scope

This document is the formal acceptance baseline for A2.

It covers only:

- real voice-loop Golden Path acceptance
- failure path acceptance for `LLM_FAILED`, `TTS_FAILED`, and `SAFETY_BLOCKED`
- regression acceptance for stale `session.failureCode`
- security follow-up for the exposed DeepSeek API key

It does not introduce new product requirements or new API fields.

## Background

The real voice loop has already been validated once end-to-end in a real request, and the stale `failureCode` carry-over issue has been fixed in code.

Relevant implementation and tests:

- [/Users/mac/Desktop/Ai-pet/src/backend_foundation/voice_loop_integration.py](/Users/mac/Desktop/Ai-pet/src/backend_foundation/voice_loop_integration.py)
- [/Users/mac/Desktop/Ai-pet/src/backend_foundation/application.py](/Users/mac/Desktop/Ai-pet/src/backend_foundation/application.py)
- [/Users/mac/Desktop/Ai-pet/src/backend_foundation/api/app.py](/Users/mac/Desktop/Ai-pet/src/backend_foundation/api/app.py)
- [/Users/mac/Desktop/Ai-pet/tests/test_backend_ai_voice_loop_integration.py](/Users/mac/Desktop/Ai-pet/tests/test_backend_ai_voice_loop_integration.py)

## API Under Test

- `POST /v1/internal/device-sessions/{sessionId}/voice-loop`

Primary response fields under acceptance:

- `session.state`
- `session.asrStatus`
- `session.llmStatus`
- `session.ttsStatus`
- `session.failureCode`
- `session.fallbackUsed`
- `runtimeFailureCode`
- `responseText`
- `audioBase64`
- `audioFormat`

## Acceptance Decision

Current control decision for A2:

- Golden Path status: `PASS`
- Functional blocking status: cleared
- Security exception status: open

Current status:

- Old key exposure: confirmed
- Key rotation: pending
- Post-rotation retest: pending as `ops-release readiness`, not as a functional blocker

## Golden Path

### Purpose

Validate the real speech-to-ASR-to-LLM-to-TTS loop with no fallback and no stale failure markers.

### Input Example

Session:

- existing bound device session
- valid DeepSeek key configured

Request example:

```json
{
  "requestId": "req-real-golden-001",
  "audioBase64": "<base64 wav payload>",
  "audioFormat": "audio/wav",
  "sampleRateHz": 16000,
  "locale": "zh-CN"
}
```

Suggested spoken text:

```text
你好，我想测试一下真实语音链路是否已经打通。
```

### Expected Output

Minimum expected response shape:

```json
{
  "session": {
    "state": "completed",
    "asrStatus": "succeeded",
    "llmStatus": "succeeded",
    "ttsStatus": "succeeded",
    "failureCode": null,
    "fallbackUsed": false
  },
  "runtimeFailureCode": "none",
  "responseText": "<non-empty>",
  "audioBase64": "<non-empty>",
  "audioFormat": "audio/wav"
}
```

### Success Acceptance Standard

The Golden Path is accepted only if all of the following are true:

1. `session.state = completed`
2. `session.failureCode = null`
3. `runtimeFailureCode = none`
4. `fallbackUsed = false`
5. `session.asrStatus = succeeded`
6. `session.llmStatus = succeeded`
7. `session.ttsStatus = succeeded`
8. `responseText` is non-empty
9. `audioBase64` is non-empty

### Current Verdict

Verdict:

- `A2 Golden Path = PASS`

Decision notes:

- The real-device voice loop is accepted as functionally complete for the frozen MVP path.
- DeepSeek key rotation and post-rotation retest remain required as a security follow-up.
- That security follow-up does not block the current MVP baseline freeze or forward progress.

## Failure Path Samples

### LLM_FAILED

Purpose:

- verify runtime fallback works when LLM generation fails

Expected result:

```json
{
  "session": {
    "state": "fallback",
    "failureCode": "LLM_FAILED",
    "fallbackUsed": true,
    "llmStatus": "failed",
    "ttsStatus": "succeeded"
  },
  "runtimeFailureCode": "llm_failed",
  "fallbackMode": "technical_recovery"
}
```

Acceptance notes:

- `session.failureCode` must be `LLM_FAILED`
- `runtimeFailureCode` must be `llm_failed`
- fallback audio/text must still be returned when TTS succeeds

### TTS_FAILED

Purpose:

- verify hard response-audio failure is surfaced as terminal failure

Expected result:

```json
{
  "session": {
    "state": "failed",
    "failureCode": "TTS_FAILED",
    "ttsStatus": "failed"
  },
  "runtimeFailureCode": "tts_failed",
  "audioBase64": null
}
```

Acceptance notes:

- `session.state` must be `failed`
- `audioBase64` must be absent or `null`
- `runtimeFailureCode` must match the current request failure, not historical session state

### SAFETY_BLOCKED

Purpose:

- verify safety fallback path is reflected in both runtime and session fields

Expected result for input block:

```json
{
  "session": {
    "state": "fallback",
    "failureCode": "SAFETY_BLOCKED",
    "fallbackUsed": true,
    "llmStatus": "skipped",
    "safetyFlag": true
  },
  "runtimeFailureCode": "safety_blocked_input"
}
```

Expected result for output block:

```json
{
  "session": {
    "state": "fallback",
    "failureCode": "SAFETY_BLOCKED",
    "fallbackUsed": true,
    "llmStatus": "succeeded",
    "safetyFlag": true
  },
  "runtimeFailureCode": "safety_blocked_output"
}
```

Acceptance notes:

- `session.failureCode` stays at backend enum `SAFETY_BLOCKED`
- `runtimeFailureCode` distinguishes input block and output block

## Regression Acceptance

### Scenario

The same `sessionId` is used across two runs:

1. first run hits `LLM_FAILED`
2. second run succeeds completely

### Expected Result

The second run must return:

```json
{
  "session": {
    "state": "completed",
    "failureCode": null,
    "fallbackUsed": false
  },
  "runtimeFailureCode": "none"
}
```

This confirms the backend no longer leaks historical `failureCode` into a later successful run.

Automated regression coverage already exists in:

- [/Users/mac/Desktop/Ai-pet/tests/test_backend_ai_voice_loop_integration.py](/Users/mac/Desktop/Ai-pet/tests/test_backend_ai_voice_loop_integration.py)

## Execution Record

### Already Verified

1. Automated integration coverage:
   - `PYTHONPATH=src python3 -m unittest tests.test_backend_ai_voice_loop_integration`
2. Backend service coverage:
   - `PYTHONPATH=src python3 -m unittest tests.test_backend_foundation`
3. A real voice-loop run previously returned:
   - `state = completed`
   - `asrStatus = succeeded`
   - `llmStatus = succeeded`
   - `ttsStatus = succeeded`
   - `fallbackUsed = false`
   - `runtimeFailureCode = none`
4. Current control decision:
   - A2 Golden Path is marked `PASS`
   - exposed DeepSeek key rotation is tracked as a security exception
   - post-rotation retest is moved to `ops-release readiness`
5. MVP baseline acceptance record:
   - Python/backend/AI/firmware-simulator baseline verification passed
   - frontend build checks are blocked by local Node/npm availability, not by a known code failure
   - baseline freeze and forward progress remain unblocked

## Security Exception

Exception:

- An exposed DeepSeek key still requires rotation.

Required follow-up:

1. Rotate the exposed DeepSeek key
2. Reconfigure runtime with the replacement key
3. Re-run one real Golden Path request during `ops-release readiness`
4. Record the returned values for:
   - `session.state`
   - `session.failureCode`
   - `runtimeFailureCode`
   - `fallbackUsed`

Non-blocking clarification:

- This exception does not change the current A2 functional PASS decision.
- This exception does not block the MVP baseline freeze.
- This exception does not block the current MVP workstream from moving forward.

## Final Sign-Off Checklist

- [x] Golden Path acceptance standard is defined
- [x] A2 Golden Path is marked `PASS`
- [x] `LLM_FAILED` sample is defined
- [x] `TTS_FAILED` sample is defined
- [x] `SAFETY_BLOCKED` sample is defined
- [x] stale `failureCode` regression standard is defined
- [x] automated regression exists
- [x] security exception has been documented as non-blocking
- [ ] exposed DeepSeek key has been rotated
- [ ] post-rotation Golden Path retest has been executed during `ops-release readiness`
- [ ] final evidence has been attached to review thread
