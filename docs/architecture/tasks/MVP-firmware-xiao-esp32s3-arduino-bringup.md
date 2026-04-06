# MVP Firmware XIAO ESP32S3 Arduino Bring-up

## Version

- `MVP`

## Task ID

- `MVP-T3 / MVP-T6`

## Current Branch

- `feat/firmware-xiao-esp32s3-arduino-bringup`

## Goal

- Add a real-device Arduino IDE bring-up for `Seeed XIAO ESP32S3 + XIAO ESP32S3 Sense`.
- Keep this branch focused on the input chain only.
- Reuse the current backend `voice-loop` request and response fields without modification.

## In Scope

- Real device boot on XIAO ESP32S3 Sense
- Wi-Fi pairing, connect, and reconnect
- `Preferences` storage for runtime config
- Board PDM microphone capture
- `POST /v1/internal/device-sessions/{sessionId}/voice-loop`
- Local state machine and error states
- Serial logging and minimum debug commands

## Out of Scope

- Local playback
- `speaking` state
- Speaker or amp chain
- Prompt and persona changes
- Backend business model changes
- Frontend and admin console work
- Payment work
- Final production transport or certificate policy

## Real-device State Machine

- `booting`
- `pairing_ready`
- `connecting_wifi`
- `wifi_connected`
- `connecting_cloud`
- `ready_to_speak`
- `listening`
- `thinking`
- `error`

## Board-level Assumptions

- MCU: `Seeed XIAO ESP32S3`
- Expansion board: `XIAO ESP32S3 Sense`
- Microphone path: onboard PDM microphone
- Current bring-up trigger: serial command instead of button or wake-word path
- Cloud session ownership stays outside firmware; firmware consumes an already-created `sessionId`

## Pin Usage

- PDM data: `GPIO41`
- PDM clock: `GPIO42`
- Serial log: USB CDC

## Runtime Config

The pairing portal stores:

- Wi-Fi SSID
- Wi-Fi password
- `cloudBaseUrl`
- `sessionId`
- `deviceId`
- `locale`

## Contract Notes

The firmware keeps the current field names unchanged:

- `requestId`
- `audioBase64`
- `audioFormat`
- `sampleRateHz`
- `durationMs`
- `locale`

Returned `audioBase64` is ignored in this branch because playback is disabled.

## Capture Duration Decision

- Current MVP default capture duration: `1500ms`
- Decision status: merged back into the real-device bring-up mainline
- Freeze status: not treated as the final production value

Decision basis:

- `500ms` already has confirmed negative real-device evidence and can land in `asr_failed` consistently.
- `1500ms` already has a confirmed real-device positive case.
- `1000ms` does not yet have enough stable evidence.
- `2000ms` adds noticeable waiting feel and extra latency.

## Dev/Test ASR Stub Note

- `AI_ASR_STUB_MODE` and `AI_ASR_STUB_TRANSCRIPT` are for `dev/test` use only.
- Default behavior is off. If `AI_ASR_STUB_MODE` is unset or empty, backend keeps the normal local mock ASR selection path.
- The fixed transcript stub is enabled only when `AI_ASR_STUB_MODE=fixed_transcript`.
- `AI_ASR_STUB_TRANSCRIPT` provides the transcript returned by the stub for any non-empty audio payload.
- This stub exists only to validate the real-device semantic loop with PCM microphone input before real ASR integration is ready.
- It does not represent real speech recognition behavior and must not be treated as the formal ASR solution for MVP or production.

## Known Risks

- The repository local mock ASR expects UTF-8 text bytes and is not suitable for real PCM microphone validation.
- HTTP JSON plus base64 payload size is acceptable for MVP bring-up but not a final transport design.
- If the target cloud uses HTTPS, certificate policy is intentionally left unresolved in this branch.
- The branch uses transport reachability for `connecting_cloud`; it does not add a new backend probe API.

## Minimum Validation Goal

- Boot reaches `pairing_ready` without crashing
- Saved config survives reboot
- Device reconnects after Wi-Fi loss
- PDM capture produces uploadable PCM payload
- Cloud request succeeds against the current minimal endpoint
- Local errors are visible on serial output

## Minimum Recheck Plan

- Mainline set: `1500ms` for `10` consecutive turns
- Control set: `1000ms` for `10` turns
- Observe at minimum:
  capture duration, bytes, samples, HTTP status, transcript presence, and `asr_failed` occurrence

## Real-device Bring-up Preparation

Before starting board validation, prepare:

- `Seeed XIAO ESP32S3` plus `XIAO ESP32S3 Sense`
- USB data cable
- Arduino IDE with `esp32` and `ArduinoJson`
- A `2.4GHz` Wi-Fi network
- Reachable `cloudBaseUrl`
- A valid `sessionId`
- Serial Monitor at `115200`

## Bring-up Operator Flow

1. Compile and flash the sketch from:
   [xiao_esp32s3_sense_bringup.ino](/Users/mac/Desktop/Ai-pet/firmware/arduino/xiao_esp32s3_sense_bringup/xiao_esp32s3_sense_bringup.ino)
2. Watch boot logs and confirm `pairing_ready` if config is missing.
3. Connect to `AI-PET-SETUP-<chip>` and open `http://192.168.4.1/`.
4. Save Wi-Fi, `cloudBaseUrl`, `sessionId`, `deviceId`, and `locale`.
5. Wait for:
   `connecting_wifi -> wifi_connected -> connecting_cloud -> ready_to_speak`
6. Send `listen` over serial to capture and upload one turn.
7. Validate success or error bucket from serial logs.

## Expected Success Log Markers

- `state -> booting | initializing board`
- `microphone ready on GPIO41/GPIO42`
- `state -> pairing_ready | stored config missing`
- `state -> wifi_connected | ip=...`
- `state -> ready_to_speak | cloud transport reachable`
- `state -> listening | capturing microphone input`
- `captured ... bytes from PDM microphone`
- `state -> thinking | uploading audio to cloud`
- `cloud http=200 session=... fallback=... failure=...`
- `state -> ready_to_speak | turn completed, playback disabled`

## Common Failure Buckets

- `wifi_connect_failed`
- `cloud_connect_failed`
- `tls_config_required`
- `mic_init_failed`
- `audio_capture_failed`
- `cloud_request_failed`
- `json_parse_failed`

## Triage Order

1. Power and USB serial
2. Mic init
3. Pairing portal
4. Wi-Fi IP acquisition
5. Cloud reachability
6. `status` config dump
7. `listen` upload
8. Response parsing

## Acceptance For Review Candidate

- Suitable for first board-on-desk validation
- Suitable for verifying input-chain bring-up on XIAO ESP32S3 Sense
- Not sufficient for playback validation
- Not sufficient for final production protocol freeze
