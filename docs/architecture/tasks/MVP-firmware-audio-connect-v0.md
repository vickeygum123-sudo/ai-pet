# MVP Firmware Audio Connect v0

## Version

- `MVP`

## Task ID

- `MVP-T3 / MVP-T6` firmware-owned portion

## Current Branch

- `feat/firmware-audio-connect-v0`

## Goal

- Establish a firmware-side MVP skeleton for device boot, Wi-Fi setup state, cloud connectivity, audio capture/playback abstraction, and the minimum device state machine.
- Enable the first device-to-cloud integration round against the current internal voice loop route without changing backend request or response fields.

## MVP Assumptions

- The repository currently has no production firmware project, so this task uses a firmware simulator and abstraction layer under `src/firmware`.
- Audio is handled as `audio/wav`, `16000Hz`, `mono` for MVP.
- The current cloud handoff remains `POST /v1/internal/device-sessions/{sessionId}/voice-loop`.
- The current `JSON + base64` voice route is acceptable for MVP integration only and is not treated as the final production transport contract.
- Session creation and bind flow remain outside firmware ownership for this branch. Firmware consumes an already-created `sessionId`.

## In Scope

- Device boot sequence.
- Wi-Fi provisioning state transitions.
- Cloud connectivity readiness check.
- Audio capture and playback abstractions.
- Minimum device state machine.
- Cloud adapter for the current internal voice-loop endpoint.
- Local status reporting hook for future telemetry wiring.

## Out of Scope

- Prompt or persona changes.
- Backend business model changes.
- Frontend or admin UI changes.
- Formal subscription or payment behavior.
- Final production streaming protocol design.
- OTA implementation beyond keeping the simulator boundary OTA-friendly.

## Minimal Device State Machine

- `booting`
- `pairing_ready`
- `connecting_wifi`
- `wifi_connected`
- `connecting_cloud`
- `ready_to_speak`
- `listening`
- `thinking`
- `speaking`
- `error`

## Firmware Boundary Notes

- Device logic stays lightweight and only owns local state, transport shaping, and I/O boundaries.
- Persona, memory, subscription, and safety policy remain cloud-owned.
- A local status reporter is included so state updates can later be forwarded to telemetry or device-status services without changing the core state machine.

## Cloud Contract Notes

- Firmware sends:
  - `requestId`
  - `audioBase64`
  - `audioFormat`
  - `sampleRateHz`
  - `durationMs`
  - `locale`
- Firmware consumes:
  - `session.state`
  - `transcript`
  - `responseText`
  - `audioBase64`
  - `audioFormat`
  - `fallbackMode`
  - `runtimeFailureCode`

## Test Strategy

- Unit-like tests for state transitions and connectivity flow.
- Integration-style tests that run the firmware simulator against the current FastAPI backend app in-process.
- Failure-path test for missing synthesized audio so the device moves into a visible error state.

## Integration Readiness

- Suitable for MVP device-to-cloud minimal integration.
- Not sufficient for production rollout until real transport, device auth, OTA flow, and hardware SDK wiring are defined and validated.
