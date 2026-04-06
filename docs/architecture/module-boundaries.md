# AI Emotional Companion Hardware Module Boundaries

## 1. Boundary Principles

- Keep the device lightweight; move intelligence to the cloud.
- Make future upgrades backend-driven whenever possible.
- Keep one branch focused on one concern.
- If a task spans modules, split it into explicit sub-tasks first.

## 2. Module Map

## Hardware / Firmware

### Responsibility

- Device boot, Wi-Fi setup, audio capture, audio playback, local controls, OTA agent, cloud connection basics.

### Should own

- Device lifecycle state.
- Local hardware capability reporting.
- Audio transport reliability.
- OTA execution.

### Should not own

- Long-term memory.
- Persona logic.
- Subscription policy.
- Safety policy beyond local fail-safe behavior.

## Frontend

### Responsibility

- User-facing web for onboarding, device binding, role settings, account, and subscription management.

### Should own

- Setup flow UX.
- Account and device pages.
- Subscription pages.
- User-facing role configuration controls.

### Should not own

- Conversation orchestration.
- Memory logic.
- Billing source of truth.

## Backend

### Responsibility

- User, device, session, role, memory metadata, subscription entitlement, operational APIs.

### Should own

- Core business objects and APIs.
- Device/account/session source of truth.
- Subscription entitlement state.
- Admin-facing query APIs.

### Should not own

- Raw model prompt authoring as the primary orchestration layer.
- Firmware behavior logic.

## AI Orchestration

### Responsibility

- ASR, LLM, TTS orchestration, persona control, memory recall/injection, safety decision chain.

### Should own

- Runtime dialogue pipeline.
- Prompt composition.
- Persona and safety enforcement during generation.
- Memory recall rules.

### Should not own

- User billing logic.
- Device ownership logic.
- Admin CRUD source of truth.

## Persona System

### Responsibility

- Role card, tone, style, relationship boundaries, configurable persona parameters.

### Should own

- Character definition.
- Tone controls.
- Relationship expression constraints.

### Should not own

- User account authority.
- Raw memory storage engine.

## Memory System

### Responsibility

- Extract, store, recall, correct, and delete user-related memory artifacts.

### Should own

- Memory schema.
- Memory extraction rules.
- Recall ranking.
- Correction and deletion path.

### Should not own

- Speech transport.
- Device state.
- Billing policy.

## Relationship Maintenance

### Responsibility

- Familiarity state, continuity cues, revisit triggers, milestone design.

### Should own

- Relationship stage model.
- Trigger rules for continuity.
- Companion lifecycle events.

### Should not own

- Raw ASR/TTS stack.
- Payment flow.

## Subscription System

### Responsibility

- Package design, entitlement logic, upgrades, expiration, downgrade behavior.

### Should own

- Subscription policy.
- Entitlement state machine.
- Payment integration boundary.

### Should not own

- Conversation core logic except for capability gating.

## Admin Console

### Responsibility

- Device status, user state, logs, audit, operations configuration, dashboards.

### Should own

- Operational visibility.
- Audit workflow.
- Config publishing tools.

### Should not own

- Primary data generation.
- Runtime conversation orchestration.

## Safety

### Responsibility

- Sensitive topic policy, content restrictions, fallback strategy, audit and escalation path.

### Should own

- Safety rules.
- Risk grading.
- Review and incident workflow.

### Should not own

- General product analytics.
- Hardware transport.

## 3. Cross-Module Split Rules

- Hardware + cloud issue: split transport reliability from cloud dialogue handling.
- Persona + memory issue: split "what should be remembered" from "how the role expresses it."
- Subscription + dialogue issue: split entitlement gating from conversation quality changes.
- Safety + children issue: create an independent child-line workstream, do not hide it inside general safety tasks.

## 4. Recommended Dialogue Types

- Total-control dialogue: roadmap, module split, acceptance gates, version decisions.
- Product dialogue: user segment, role concept, free vs paid value.
- Architecture dialogue: end-to-end flow, interfaces, storage, orchestration, safety chain.
- Frontend dialogue: onboarding site, account center, subscription pages.
- Backend dialogue: user/device/session/subscription/memory APIs.
- AI dialogue: prompts, routing, persona engine, memory recall, safety logic.
- Firmware dialogue: device boot, audio path, OTA, connectivity.
- Admin dialogue: dashboards, logs, config, audit tools.

## 5. Merge Guidance

- Planning docs can merge to main after review if they stay documentation-only.
- Any branch mixing roadmap work and implementation work should be split before merge.
- Cross-module implementation should merge only after boundaries, interface contracts, and test coverage are clear.
