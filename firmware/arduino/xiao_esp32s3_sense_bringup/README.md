# XIAO ESP32S3 Sense Arduino Bring-up

This sketch is the MVP real-device bring-up for `Seeed XIAO ESP32S3 + XIAO ESP32S3 Sense`.

Scope for this sketch:

- Boot and local state machine
- Wi-Fi pairing, connect, and reconnect
- `Preferences` storage for Wi-Fi and cloud config
- Board PDM microphone capture
- Current `/v1/internal/device-sessions/{sessionId}/voice-loop` JSON/base64 upload
- MAX98357 I2S playback for returned TTS WAV audio
- Serial logs and minimum debug commands

Explicitly out of scope in this sketch:

- Backend field changes
- Frontend or admin console work
- Prompt or persona changes
- Final HTTPS certificate strategy

## Directory

- `xiao_esp32s3_sense_bringup.ino`: main sketch
- `BringupConfig.h`: editable defaults and feature flags

## Arduino IDE Setup

1. Install `esp32` board support from Espressif in Arduino IDE.
2. Install `ArduinoJson`.
3. Open `firmware/arduino/xiao_esp32s3_sense_bringup/xiao_esp32s3_sense_bringup.ino`.
4. Board:
   `Seeed XIAO ESP32S3`
5. USB CDC On Boot:
   enabled
6. Partition scheme:
   choose one with enough app space for HTTP and JSON bring-up

## Pairing Flow

When stored config is missing or cleared, the device enters `pairing_ready` and starts a soft AP:

- SSID: `AI-PET-SETUP-<chip>`
- Password: `petsetup`
- Page: `http://192.168.4.1/`

The page stores:

- Wi-Fi SSID and password
- `cloudBaseUrl`
- `sessionId`
- `deviceId`
- `locale`

Current default locale for Tencent ASR validation is `zh-CN`.

## Serial Commands

- `help`: print commands
- `status`: print current state and config summary
- `pairing`: reopen pairing portal
- `listen`: capture one audio turn and upload it
- `reconnect`: force Wi-Fi and cloud reconnect
- `clear`: erase stored config and reopen pairing mode

## Current Cloud Contract

The sketch keeps the existing backend field names unchanged:

- `requestId`
- `audioBase64`
- `audioFormat`
- `sampleRateHz`
- `durationMs`
- `locale`

Response handling logs:

- `session.state`
- `transcript`
- `responseText`
- `audioFormat`
- `fallbackMode`
- `runtimeFailureCode`

Returned `audioBase64` is decoded on-device and played through MAX98357 when the response is
`audio/wav`.

## Capture Duration Decision

The current MVP default capture strategy is `lightweight VAD`, with a fixed-window fallback still available.

Current real-device conclusion:

- `500ms` has a confirmed negative pattern and can fall into `asr_failed` consistently.
- `1500ms` has a confirmed real-device positive case and is now the bring-up mainline default.
- `1000ms` does not yet have enough stable evidence.
- `2000ms` increases waiting feel and end-to-end latency noticeably.

Current rule for this branch:

- `lightweight VAD` replaces the fixed `1500ms` window as the default capture strategy.
- `1500ms` remains the safe rollback baseline and the no-speech fallback boundary.
- The request/response protocol stays unchanged.
- This is an MVP tuning set and not yet the final production freeze value.

## Lightweight VAD State Machine

- `priming`: sample the first `60ms` to estimate ambient noise floor.
- `waiting_for_speech`: keep listening for speech onset while adapting the noise floor on quiet frames.
- `speaking`: speech has started; keep recording and preserve `300ms` of pre-roll.
- `trailing_silence`: after speech, accumulate the initial tail-silence budget.
- `confirming_end`: once silence reaches the end threshold, open a short confirmation window; only if it stays quiet does the turn actually end.
- `post_speech_guard`: if the tail still jitters for too long during `confirming_end`, force a final endpoint instead of drifting to `max_capture`.
- `fallback_fixed_window`: if no speech is detected by `1500ms`, end as the old baseline window.
- `complete`: stop when either `end_of_speech` or `max_capture` is reached.

## Recommended VAD Parameters

- `frameMs=20`: small enough for responsive detection without overloading the loop.
- `bootstrapMs=60`: further reduces the chance that speech onset is absorbed into the initial noise estimate.
- `preRollMs=300`: keeps more leading context so short Chinese phrases are less likely to lose the first syllable.
- `minCaptureMs=640`: still blocks accidental spikes, but allows valid short utterances to finish sooner.
- `maxCaptureMs=6000`: keeps `max_capture` as a safety guard instead of the main way a normal sentence ends.
- `endSilenceMs=460`: the user must stay quiet a bit longer before the turn becomes a true end candidate.
- `endConfirmMs=100`: after reaching the silence threshold, use a short final confirmation window before ending.
- `startThreshold=max(64, noiseFloor*1.25 + 6)`: makes start detection less conservative in real-device noise while keeping an absolute floor.
- `endThreshold=max(45, noiseFloor*1.5 + 12)`: use a lower release threshold to add hysteresis and prevent chatter.
- `resumeThreshold=endThreshold + 24`, `resumeFrames=4`: require a stronger, sustained rebound before leaving `trailing_silence`, which reduces tail jitter and `max_capture`.
- `speech resumed => trailingSilenceMs=0`: once the user clearly resumes speaking, end detection restarts from a fresh silence run.
- `postSpeechMaxMs=1400`: if the tail keeps jittering after a real stop attempt, allow a larger final buffer before forcing an endpoint.
- `postSpeechGuardMinSilenceMs=240`: the guard only applies after a more meaningful amount of current silence has already accumulated.
- `tailWindowStartedAtMs` resets on each new `trailing_silence`: the guard now follows the latest tail attempt instead of the first brief pause in the sentence.
- `post_speech_guard` only fires while the state is still `confirming_end`: if the user has clearly resumed speaking, the guard no longer ends the turn mid-speech.

## Switching Between VAD And Fixed Window

- `AI_PET_ENABLE_LIGHTWEIGHT_VAD=1`: use the new VAD-first capture flow.
- `AI_PET_ENABLE_LIGHTWEIGHT_VAD=0`: fully roll back to the old fixed `1500ms` window.
- Even when VAD is enabled, if no speech is detected before `1500ms`, the sketch falls back to the current baseline window behavior.

## Important Integration Notes

- The default repository test backend uses a mock ASR that treats audio bytes as UTF-8 text. Real PDM PCM audio will not transcribe meaningfully against that mock path.
- For Tencent ASR Chinese validation, the firmware default locale is `zh-CN` so the backend can route to `16k_zh` by default.
- If a board already stored `locale=en-US` in `Preferences`, changing the default in code is not enough by itself. Re-save the pairing form or run `clear` and pair again so the board stops sending `en-US`.
- If your target cloud endpoint uses `https://`, this sketch intentionally stops and reports a TLS configuration blocker unless you explicitly allow insecure TLS in `BringupConfig.h`.
- `cloud connected` is implemented as transport reachability to the configured host and port. It does not depend on adding a new backend probe route.
- Playback currently supports `audio/wav` with PCM `16-bit` mono or stereo payloads. Mono WAV is duplicated to stereo before I2S TX so MAX98357 can play it reliably.
- No cloud protocol changes are required for playback; WAV sample rate is read from the returned file header.

## Hardware Pins

- PDM data: `GPIO41`
- PDM clock: `GPIO42`
- MAX98357 BCLK: `GPIO7` (`D8`)
- MAX98357 LRC / WS: `GPIO8` (`D9`)
- MAX98357 DIN: `GPIO9` (`D10`)
- Serial log: USB CDC

## Minimum Bring-up Checklist

1. Flash sketch and open serial monitor at `115200`.
2. Confirm boot log reaches `pairing_ready`.
3. Join `AI-PET-SETUP-<chip>` and save Wi-Fi plus cloud config.
4. Confirm `connecting_wifi -> wifi_connected -> connecting_cloud -> ready_to_speak`.
5. Send `listen` over serial and verify capture, upload, WAV decode, and audible playback.
6. Power-cycle device and confirm credentials survive reboot.
7. Turn Wi-Fi off and back on to observe reconnect behavior.

## Real-device Preparation

Before you power the board for bring-up, confirm:

1. Hardware is `Seeed XIAO ESP32S3` with the `XIAO ESP32S3 Sense` addon attached correctly.
2. USB cable supports both power and data. Charge-only cables are a common blocker.
3. Arduino IDE already has:
   `esp32` by Espressif and `ArduinoJson`.
4. Board selection is:
   `Seeed XIAO ESP32S3`
5. You know a reachable backend base URL on the same network as the board.
6. You already have a usable `sessionId` from the current backend flow.
7. Your Wi-Fi is `2.4GHz`; many ESP32 bring-up failures are actually `5GHz-only` SSIDs.
8. Serial Monitor is set to:
   `115200 baud`, `No line ending` or `Newline` depending on how you send commands.

## Arduino IDE Build And Flash

1. Open Arduino IDE.
2. Open [`xiao_esp32s3_sense_bringup.ino`](/Users/mac/Desktop/Ai-pet/firmware/arduino/xiao_esp32s3_sense_bringup/xiao_esp32s3_sense_bringup.ino).
3. Open [`BringupConfig.h`](/Users/mac/Desktop/Ai-pet/firmware/arduino/xiao_esp32s3_sense_bringup/BringupConfig.h) and check at least:
   `AI_PET_DEFAULT_CLOUD_BASE_URL`
4. Tools settings:
   `Board = Seeed XIAO ESP32S3`
   `USB CDC On Boot = Enabled`
   `Partition Scheme = any scheme with enough app space`
5. Click Verify.
6. Connect the board over USB-C.
7. Select the correct serial port.
8. Click Upload.
9. If upload fails, hold `BOOT`, tap `RESET`, then retry upload.
10. Open Serial Monitor and confirm the banner appears.

## Pairing And Wi-Fi Setup

1. After boot, if config is missing, the board enters `pairing_ready`.
2. Connect your phone or laptop to:
   `AI-PET-SETUP-<chip>`
3. Password:
   `petsetup`
4. Open:
   `http://192.168.4.1/`
5. Fill in:
   Wi-Fi SSID, Wi-Fi password, `cloudBaseUrl`, `sessionId`, `deviceId`, `locale`
   For Tencent ASR Chinese validation, set `locale=zh-CN`.
6. Click `Save And Reconnect`.
7. Go back to Serial Monitor and wait for:
   `connecting_wifi -> wifi_connected -> connecting_cloud -> ready_to_speak`

## Record And Upload Flow

1. In Serial Monitor, send:
   `status`
2. Confirm state is `ready_to_speak`.
3. Send:
   `listen`
4. Speak near the onboard microphone during the capture window.
5. Watch for:
   `state -> listening`
   `capture strategy=lightweight_vad frameMs=20 minMs=640 maxMs=6000 fallbackFixedMs=1500`
   `vad state -> priming`
   `vad state -> waiting_for_speech`
   `vad state -> speaking`
   `vad state -> trailing_silence`
   `vad state -> confirming_end`
   `captured durationMs=... bytes=... samples=... speechDetected=true`
   `state -> thinking`
   `cloud http=...`
   `state -> speaking`
   `decoded cloud audio format=audio/wav`
   `wav parsed sampleRateHz=... bitsPerSample=16 channels=... pcmBytes=...`
   `playback done durationMs=...`
   `turn summary | strategy=... durationMs=... exit=... transcript=... fallback=... failure=...`
   `state -> ready_to_speak | turn completed with playback`
6. If you want to retry connectivity before another turn, send:
   `reconnect`

## Expected Success Logs

### First boot with no stored config

```text
AI Pet XIAO ESP32S3 Sense bring-up
firmware=0.1.0-xiao-bringup playback=enabled
[bringup] state -> booting | initializing board
[bringup] deviceId=xiao-esp32s3-sense-12AB34
[bringup] cloudBaseUrl=http://192.168.1.2:8000
[bringup] microphone ready on GPIO41/GPIO42
[bringup] playback ready on MAX98357 BCLK=7 LRC=8 DIN=9
[bringup] state -> pairing_ready | stored config missing
[bringup] pairing portal ready at http://192.168.4.1/
Commands:
  help       - show commands
  status     - print state and config summary
  pairing    - start pairing portal
  listen     - capture one turn and upload it
  reconnect  - force Wi-Fi and cloud reconnect
  clear      - erase stored config and reopen pairing mode
```

### Save config and connect successfully

```text
[bringup] state -> connecting_wifi | joining YourWiFi
....
[bringup] state -> wifi_connected | ip=192.168.1.88
[bringup] state -> connecting_cloud | probing cloud transport
[bringup] state -> ready_to_speak | cloud transport reachable
```

### Successful record and upload

```text
[bringup] state -> listening | capturing microphone input
[bringup] capture strategy=lightweight_vad frameMs=20 minMs=640 maxMs=6000 fallbackFixedMs=1500
[bringup] vad state -> priming | measuring ambient noise floor
[bringup] vad state -> waiting_for_speech | noiseFloor=28
[bringup] vad state -> speaking | frameEnergy=132 noiseFloor=18 startThreshold=64 speechStartMs=220
[bringup] vad state -> trailing_silence | frameEnergy=34 endThreshold=45
[bringup] vad state -> confirming_end | trailingSilenceMs=460 confirmMs=100
[bringup] vad state -> complete | reason=end_of_speech_confirmed speechDurationMs=1540 trailingSilenceMs=560 confirmMs=100
[bringup] captured durationMs=1080 bytes=34560 samples=17280 speechDetected=true
[bringup] state -> thinking | uploading audio to cloud
[bringup] cloud http=200 session=completed fallback=none failure=none audioFormat=audio/wav
[bringup] transcript: hello there
[bringup] responseText: I am here with you. What feels most present right now?
[bringup] state -> speaking | decoding and playing cloud audio
[bringup] decoded cloud audio format=audio/wav base64Bytes=28844 decodedBytes=21632
[bringup] wav parsed sampleRateHz=24000 bitsPerSample=16 channels=1 pcmBytes=21588
[bringup] playback done durationMs=922 sampleRateHz=24000 inputChannels=1 outputChannels=2 pcmBytes=43176
[bringup] turn summary | strategy=lightweight_vad durationMs=1080 exit=end speechDetected=true transcript=hello there fallback=none failure=none
[bringup] state -> ready_to_speak | turn completed with playback
```

## Common Failure Logs

### Wi-Fi credentials wrong or AP unreachable

```text
[bringup] state -> connecting_wifi | joining WrongWiFi
....
[bringup] state -> error | wifi_connect_failed | timed out while joining configured network
[bringup] state -> pairing_ready | Wi-Fi connect failed, waiting for updated config
[bringup] pairing portal ready at http://192.168.4.1/
```

### Cloud base URL wrong or backend host unreachable

```text
[bringup] state -> wifi_connected | ip=192.168.1.88
[bringup] state -> connecting_cloud | probing cloud transport
[bringup] state -> error | cloud_connect_failed | TCP transport connect failed
```

### HTTPS configured but no CA or insecure override

```text
[bringup] state -> connecting_cloud | probing cloud transport
[bringup] state -> error | tls_config_required | HTTPS endpoint configured without CA certificate or insecure override
```

### PDM microphone init failed

```text
[bringup] state -> booting | initializing board
[bringup] deviceId=xiao-esp32s3-sense-12AB34
[bringup] cloudBaseUrl=http://192.168.1.2:8000
[bringup] state -> error | mic_init_failed | i2s_driver_install failed
```

### Capture failed during `listen`

```text
[bringup] state -> listening | capturing microphone input
[bringup] state -> error | audio_capture_failed | i2s_read failed
```

### Voice-loop request failed

```text
[bringup] state -> thinking | uploading audio to cloud
[bringup] state -> error | cloud_request_failed | POST failed: connection refused
```

### Cloud returned non-JSON or unexpected body

```text
[bringup] state -> thinking | uploading audio to cloud
[bringup] state -> error | json_parse_failed | deserializeJson failed: InvalidInput
```

### Cloud returned no playable audio

```text
[bringup] state -> speaking | decoding and playing cloud audio
[bringup] state -> error | cloud_audio_missing | cloud response did not include audioBase64
```

### Cloud returned unsupported playback format

```text
[bringup] state -> speaking | decoding and playing cloud audio
[bringup] state -> error | playback_unsupported | cloud audioFormat is not supported for playback: audio/mpeg
```

## Debug And Triage Order

Use this order so you do not chase the wrong layer:

1. Confirm board powers on and Serial Monitor prints the boot banner.
2. Confirm microphone init succeeds:
   look for `microphone ready on GPIO41/GPIO42`
3. Confirm playback init succeeds:
   look for `playback ready on MAX98357 BCLK=7 LRC=8 DIN=9`
4. Confirm pairing portal appears if config is missing.
5. Confirm Wi-Fi joins and gets an IP.
6. Confirm cloud reachability before testing `listen`.
7. Confirm `status` shows the expected `cloudBaseUrl`, `deviceId`, and `sessionId`.
8. Only after connectivity is stable, run `listen`.
9. If upload fails, separate:
   `cloud connect failed` from `cloud request failed` from `json parse failed`
10. If transcript looks wrong but request succeeded, remember the current local mock backend does not do real PCM ASR.
11. If transcript is empty, compare the serial `capture target` and `captured durationMs/bytes/samples`
    against the expected `1500ms / 48000 bytes / 24000 samples` before looking at the ASR adapter.

## Acceptance Checklist For This Round

- Board boots and prints the expected banner.
- `pairing_ready` can be entered without crashing.
- Pairing portal stores config and reconnects automatically.
- Reboot preserves stored config through `Preferences`.
- Device reaches `ready_to_speak`.
- Serial `listen` captures microphone bytes without crashing.
- Device can POST one real audio turn to the current `/voice-loop` route.
- Device decodes returned `audioBase64` as WAV and sends PCM to MAX98357 over I2S.
- Speaker outputs an audible TTS response for a successful turn.
- Serial log clearly shows success or the correct failure bucket.
- `clear` returns the board to pairing mode.

## Minimum Recheck Plan After Mainline Merge

- `1500ms`: run `10` consecutive real-device turns as the mainline validation set.
- `1000ms`: run `10` real-device turns as the control comparison set.
- Record at minimum for each turn:
  state flow, capture duration, byte count, sample count, backend HTTP status, transcript presence, and whether it fell into `asr_failed`.
