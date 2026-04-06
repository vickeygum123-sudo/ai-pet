# AI Emotional Companion Hardware Product Roadmap

## 1. Product Positioning

- Product type: AI voice companion hardware with cloud-first intelligence.
- Core value: long-term emotional companionship instead of one-shot Q&A.
- Entry point: lightweight hardware device.
- Core moat: character consistency, relationship continuity, long-term memory, cloud operations.

## 2. Target User Strategy

### Recommendation

- Main launch line: young people.
- Deferred branch: children.

### Why split

- Young people and children should not share the same launch route.
- A child-first route requires guardian system, strict content whitelist, usage limits, audit flows, and stronger compliance controls.
- Launching both together would slow down the first version and weaken character expression for the young-people line.

## 3. Version Plan

## MVP

### Core goal

- Verify that users will repeatedly talk to one fixed AI companion through hardware.

### What to validate

- Can the device onboarding and first conversation run end to end.
- Does the role feel distinct enough to create attachment.
- Do users return within 7 days.
- Is the safety baseline controllable.

### In scope

- One hardware form factor.
- One main role direction.
- Basic ASR -> dialogue -> TTS cloud loop.
- Lightweight memory: profile + short-term continuity.
- Basic web for account, device binding, and simple role setting.
- Basic admin panel for device status, sessions, and errors.

### Out of scope

- Children mode.
- Multi-role marketplace.
- Advanced subscription packages.
- UGC role creation.
- Complex operations tooling.
- Social features.
- Full app ecosystem.

### Module depth

| Module | MVP depth |
| --- | --- |
| Hardware / Firmware | Wi-Fi setup, mic/speaker loop, device state, basic OTA hook |
| Cloud Dialogue | Stable speech-to-dialogue-to-speech orchestration |
| Character Persona | Fixed role card, speaking style, topic boundaries |
| Long-term Memory | User profile and recent continuity only |
| Relationship Maintenance | Simple continuity, no full relationship state machine |
| Account System | Register, bind device, ownership |
| Subscription System | Capability flags only, no full billing required |
| Admin Console | Device/session/error visibility |
| Safety | P0 filtering, fallback responses, manual review entry |

### Exit criteria

- New user can finish setup and bind the device.
- Device can complete stable voice sessions.
- Role persona remains recognizable across sessions.
- System can reference recent continuity in follow-up chats.
- Team can inspect device/session failures in backend tools.
- No obvious P0 safety gap in normal use.

## V1

### Core goal

- Verify that memory continuity and relationship continuity improve retention and create subscription value.

### What to validate

- Users clearly feel remembered.
- Memory recall improves session quality and return rate.
- Users understand and accept subscription value around continuity and enhanced experience.

### In scope

- Formal subscription and entitlement handling.
- Long-term memory v1.
- Relationship state and milestone logic.
- Persona configuration center.
- Stronger safety and operational tooling.

### Out of scope

- Child product launch.
- Open role creation ecosystem.
- Multi-device family system.

### Module depth

| Module | V1 depth |
| --- | --- |
| Hardware / Firmware | OTA stability, reconnect recovery, remote config basics |
| Cloud Dialogue | Interruption handling, timeout recovery, model routing basics |
| Character Persona | Multiple templates with configurable parameters |
| Long-term Memory | Event extraction, preference memory, recall rules, correction path |
| Relationship Maintenance | Familiarity stages, milestones, continuous topics, revisit hooks |
| Account System | Device unbind, history view, permissions |
| Subscription System | Payment, entitlements, expiration, downgrade logic |
| Admin Console | User relationship, memory hit rate, member state, audit tools |
| Safety | Sensitive topic grading, review workflow, youth isolation pre-design |

### Exit criteria

- Memory can be recalled with stable quality.
- Users can perceive continuity across multiple days.
- Subscription rights and downgrade behavior are clear and stable.
- Backend can support operations, complaints, and safety review.

## V2

### Core goal

- Turn the product from a working companion device into an operable and scalable platform.

### What to validate

- Quality and cost can be balanced at scale.
- Content and operations can drive retention.
- Product is ready to branch into a dedicated child line if approved.

### In scope

- Cost governance and model routing.
- Content and activity operations.
- Fleet management and diagnostics.
- Experimentation and growth framework.
- Child-line go/no-go review.

### Out of scope

- Wide open platform ecosystem.
- Heavy social graph.
- Third-party skill marketplace at launch.

### Module depth

| Module | V2 depth |
| --- | --- |
| Hardware / Firmware | Batch OTA, diagnostics, version governance |
| Cloud Dialogue | Cost tiers, routing policy, quality safeguards |
| Character Persona | Role library, campaign scripts, operational events |
| Long-term Memory | Structured memory governance, edit/delete support |
| Relationship Maintenance | Rhythm-based re-engagement, milestones, lifecycle touchpoints |
| Account / Subscription | Retention operations, win-back, segmented membership |
| Admin Console | Experimentation, content ops, quality dashboards |
| Safety | Guardian, audit, usage control, and child-line controls if approved |

### Exit criteria

- Model cost enters target range.
- OTA and fleet operations are manageable.
- Operations can run campaigns and inspect impact.
- Team can make a clear child-line go/no-go decision.

## 4. Version Gate Rules

- Do not move from MVP to V1 until the team confirms repeat-use behavior exists.
- Do not move from V1 to V2 until memory and subscription value are both validated.
- Do not launch children line until its safety, guardian, and compliance requirements are independently scoped.

## 5. Suggested Next Planning Topics

- Topic 1: freeze launch user, value proposition, and free/subscription boundary.
- Topic 2: define MVP end-to-end architecture and data flow.
- Topic 3: split MVP into engineering-ready task cards.
