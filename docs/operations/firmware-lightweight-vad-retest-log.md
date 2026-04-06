# Firmware Lightweight VAD Real-device Retest Log

## Scope

- Branch: `feat/firmware-lightweight-vad-v0`
- Goal: validate lightweight VAD on real hardware without changing protocol or backend fields
- Merge decision: `do not merge to main until this retest is reviewed`

## How To Record One Round

1. Flash the latest sketch on the target board.
2. Open serial monitor and confirm the board reaches `ready_to_speak`.
3. Send `listen`.
4. Speak one target phrase.
5. Copy the single `turn summary | ...` line.
6. Fill the subjective judgment columns:
   `首字是否被吃`
   `句尾是否被截断`
   `连续多轮是否稳定`

## Serial Line To Capture

```text
[bringup] turn summary | strategy=lightweight_vad durationMs=1080 exit=end speechDetected=true transcript=你好 fallback=none failure=none
```

## Final Focused Retest

- Goal 1: short-phrase first syllable
  Use `你好` for repeated short-turn checks.
- Goal 2: long-phrase tail completeness
  Use `如果今天下雨了，我应该带什么出门？`
- Goal 3: later turns in a continuous run
  Repeat `你好` after several earlier successful turns and watch turns `6+`.

## Retest Table

| Round | Focus | Phrase | durationMs | exit | transcript | failure/fallback | 首字是否被吃 | 句尾是否被截断 | 连续多轮是否稳定 | Notes |
| --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | 短句首字 | 你好 |  |  |  |  |  |  |  |  |
| 2 | 短句首字 | 你好 |  |  |  |  |  |  |  |  |
| 3 | 长句句尾 | 如果今天下雨了，我应该带什么出门？ |  |  |  |  |  |  |  |  |
| 4 | 长句句尾 | 如果今天下雨了，我应该带什么出门？ |  |  |  |  |  |  |  |  |
| 5 | 连续 turn 预热 | 你好 |  |  |  |  |  |  |  |  |
| 6 | 连续 turn 后几轮 | 你好 |  |  |  |  |  |  |  |  |
| 7 | 连续 turn 后几轮 | 你好 |  |  |  |  |  |  |  |  |
| 8 | 连续 turn 后几轮 | 你好 |  |  |  |  |  |  |  |  |

## Acceptance Shortcut

- `durationMs` is not always fixed at `1500`
- `exit` remains mostly `end`, not frequently `fallback` or `max_capture`
- short phrase keeps the first word or syllable
- long phrase keeps the tail semantics instead of stopping early
- later turns in a continuous run do not drift into empty transcript or obvious misrecognition
- `failure/fallback` stays `none` in the mainline case
- `首字是否被吃 = 否`
- `句尾是否被截断 = 否`
- `连续多轮是否稳定 = 是`

## Return Format

When you send the retest result back, keep only these fields per round:

1. `durationMs`
2. `exit`
3. `transcript`
4. `failure/fallback`
5. `首字是否被吃`
6. `句尾是否被截断`
7. `连续多轮是否稳定`
