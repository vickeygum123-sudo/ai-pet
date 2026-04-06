# MVP Firmware Lightweight VAD v0

## Current Branch

- `feat/firmware-lightweight-vad-v0`

## Task Boundary

- Design and implement an MVP lightweight VAD capture strategy on firmware.
- Keep the current `/voice-loop` request and response fields unchanged.
- Do not change backend schema, frontend flows, playback path, payment path, or cloud protocol.

## Subtasks

1. Split firmware capture into `fixed_window` and `lightweight_vad` strategies.
2. Add a lightweight VAD state machine for speech start and speech end detection.
3. Keep `1500ms` as the rollback baseline and no-speech fallback boundary.
4. Document parameter recommendations, switch strategy, and minimum real-device retest steps.

## VAD State Machine

- `priming`
  Measure the first `60ms` of ambient audio and build the initial noise floor.
- `waiting_for_speech`
  Read `20ms` frames, update the noise floor on quiet frames, and wait for `2` consecutive speech frames.
- `speaking`
  Once speech is detected, keep recording and include `300ms` of pre-roll so the first syllable is not cut off.
- `trailing_silence`
  After speech, count low-energy frames until the turn becomes a candidate for ending.
- `confirming_end`
  Once trailing silence reaches `300ms`, open a short `80ms` confirmation window. If the user stays quiet, end normally; if speech clearly resumes, go back to `speaking`.
- `post_speech_guard`
  If the tail still jitters during `confirming_end`, allow only a bounded extra window before forcing a normal endpoint instead of drifting to `max_capture`.
- `fallback_fixed_window`
  If no speech is detected by `1500ms`, stop with the current fixed-window baseline behavior.
- `complete`
  Stop because either end-of-speech fired or total capture reached `3600ms`.

## Parameter Recommendation

- `frameMs=20`
  Balances responsiveness and loop overhead.
- `bootstrapMs=60`
  Further reduces the chance that speech onset is folded into the initial noise estimate.
- `preRollMs=300`
  Adds more lead-in protection for short Chinese phrases.
- `minCaptureMs=640`
  Keeps spike protection but allows a valid short phrase to stop earlier.
- `maxCaptureMs=6000`
  Keeps `max_capture` as a safety guard instead of the main way a normal sentence ends.
- `endSilenceMs=460`
  The user must stay quiet a bit longer before the turn becomes eligible to enter end confirmation.
- `endConfirmMs=100`
  The user must stay quiet for one short extra confirmation window before the turn ends.
- `startThreshold=max(64, noiseFloor*1.25 + 6)`
  Makes start detection less conservative in noisy real-device conditions.
- `endThreshold=max(45, noiseFloor*1.5 + 12)`
  Lower than the start threshold to provide hysteresis and avoid state flapping.
- `resumeThreshold=endThreshold + 24`, `resumeFrames=4`
  Prevents a short rebound from bouncing `trailing_silence` back to `speaking`.
- `speech resumed => trailingSilenceMs=0`
  Once the user clearly resumes speaking, end detection restarts from a fresh silence run.
- `postSpeechMaxMs=1400`
  Once tail settling starts, allow a larger final buffer before forcing an endpoint.
- `postSpeechGuardMinSilenceMs=240`
  The tail guard only applies after a meaningful amount of current silence has already accumulated.
- `tailWindowStartedAtMs` resets on each new trailing-silence entry
  The guard now follows the latest tail attempt instead of the first brief pause inside the sentence.
- `post_speech_guard` only fires while still in `confirming_end`
  If the user has clearly resumed speaking, the guard does not end the turn mid-speech.

## How It Switches From Fixed Window

- Primary path: `AI_PET_ENABLE_LIGHTWEIGHT_VAD=1`
- Rollback path: `AI_PET_ENABLE_LIGHTWEIGHT_VAD=0`
- Safety fallback while VAD is enabled:
  If speech onset is never detected before `1500ms`, capture ends at the old fixed-window baseline.

## Minimum Test Steps

1. In Arduino IDE, verify and flash the updated sketch.
2. Confirm serial log reaches `ready_to_speak`.
3. Send `listen` and speak a short Chinese phrase such as `你好` or `今天天气怎么样`.
4. Confirm serial log contains:
   `capture strategy=lightweight_vad`
   `vad state -> priming`
   `vad state -> waiting_for_speech`
   `vad state -> speaking`
   `captured durationMs=... speechDetected=true`
5. Confirm cloud request still succeeds and transcript returns.
6. Repeat with a shorter utterance and a slightly longer utterance to verify:
   capture is no longer always fixed at `1500ms`
   the beginning of speech is not clipped
   the tail is not cut too early
7. Set `AI_PET_ENABLE_LIGHTWEIGHT_VAD=0`, reflash, and confirm rollback still behaves as the old `1500ms` fixed window.

## Acceptance Standard

- Firmware still uses the current request fields: `requestId`, `audioBase64`, `audioFormat`, `sampleRateHz`, `durationMs`, `locale`.
- No backend field or protocol change is required.
- Capture duration becomes variable under VAD and remains bounded.
- Short Chinese phrases are less likely to lose their first or last syllable compared with the old fixed window.
- No-speech and rollback cases still have a safe fallback path.
- Serial logs are sufficient to identify whether speech start, speech end, fallback, or max-capture exit occurred.

## Real-device Retest Recommendation

- Suitable for real-device retest.
- Not yet recommended to merge back to `main` before at least one focused board retest round confirms:
  Chinese short phrases are no longer obviously truncated
  false triggers stay acceptable in the target environment
  memory usage remains stable during repeated turns
