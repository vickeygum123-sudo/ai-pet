# MVP-T2 Define Core Scenarios and Success Metrics

## Task Metadata

| Field | Value |
| --- | --- |
| Task ID | MVP-T2 |
| Title | Define core scenarios and success metrics |
| Primary module | Product |
| Related modules | Data, AI Orchestration, Frontend, Backend, Admin |
| Type | product |
| Priority | P0 |
| Branch suggestion | `docs/mvp-t2-scenarios-metrics` |
| Merge rule | Documentation-only, can merge to `main` after review |
| Status | done |

## 1. Decision Summary

- MVP success is not defined by total feature breadth.
- MVP success is defined by whether users form a repeatable daily-use habit with one companion role.
- The first version should optimize for short, frequent, emotionally meaningful conversations.
- Metrics should measure activation, session quality, continuity, return behavior, and safety.

## 2. Core Scenario Set

### S1. End-of-day emotional decompression

#### User intent

- "I want to talk for a few minutes after a tiring day."

#### Why it matters

- This is the highest-probability daily habit scenario.
- It fits dedicated hardware better than broad task execution.
- It naturally benefits from continuity and memory.

#### MVP requirements

- Fast wake-to-response flow.
- Warm and stable tone.
- Ability to ask follow-up questions naturally.
- Ability to remember recent emotional context the next time.

### S2. Casual companionship when alone

#### User intent

- "I do not need help with a task. I just want something familiar to talk to."

#### Why it matters

- This tests companionship directly instead of assistant utility.
- It validates whether persona consistency has enough pull by itself.

#### MVP requirements

- Role feels recognizable within the first 1-2 exchanges.
- Responses avoid generic "assistant" framing.
- Conversations can continue without requiring a task-oriented prompt.

### S3. Lightweight daily check-in

#### User intent

- "I want a quick, low-effort daily interaction."

#### Why it matters

- This supports habit formation and increases return opportunities.
- It creates repeated memory touchpoints without requiring long sessions.

#### MVP requirements

- Device and cloud latency feel low enough for quick interactions.
- Role can initiate or support simple daily rituals.
- System can connect today with what the user said recently.

### S4. Follow-up on prior topics

#### User intent

- "I want the companion to remember and continue what we were talking about."

#### Why it matters

- This is the clearest early proof of relationship continuity.
- It creates the bridge to future subscription value.

#### MVP requirements

- Basic continuity memory across recent sessions.
- Recall should be selective and relevant, not overly broad.
- Follow-up should feel natural rather than forced.

## 3. De-prioritized Scenarios

- Productivity assistant behavior.
- Knowledge-heavy factual Q&A.
- Smart home orchestration.
- Therapeutic or medical framing.
- Education and child tutoring.
- Household multi-user sharing.

## 4. Success Metric Framework

## A. Activation Metrics

These answer whether users can reach first value.

| Metric | Definition | MVP intent |
| --- | --- | --- |
| Device bind completion rate | Bound devices / setup starts | Setup is not a major drop-off point |
| First conversation completion rate | Users who complete at least 1 full voice session / bound users | Users reach the core experience quickly |
| Time to first conversation | Time from successful bind to first completed session | First value arrives with low friction |

## B. Session Quality Metrics

These answer whether the experience feels usable and companion-like.

| Metric | Definition | MVP intent |
| --- | --- | --- |
| Voice loop success rate | Sessions without ASR/TTS/orchestration failure / total sessions | Core loop is stable |
| Median first-response latency | Time from end of user speech to first audio response | Companion feels responsive |
| Session completion rate | Sessions that end normally / total started sessions | Conversations are not breaking early |
| User frustration termination rate | Sessions ended after repeated failure, fallback, or interruption | Bad sessions are contained |

## C. Continuity Metrics

These answer whether the product feels like a continuing relationship.

| Metric | Definition | MVP intent |
| --- | --- | --- |
| Recent-memory recall hit rate | Sessions where system uses relevant recent continuity / eligible sessions | Continuity exists in practice |
| Continuity satisfaction tag rate | Sampled sessions judged as "felt remembered" / reviewed continuity sessions | Recall improves user perception |
| Revisit topic rate | Sessions that naturally continue a prior topic / repeat-user sessions | Relationship is not stateless |

## D. Habit and Retention Metrics

These answer whether users come back.

| Metric | Definition | MVP intent |
| --- | --- | --- |
| D1 return rate | Users active on day 1 after first day / activated users | Some repeat value exists immediately |
| D7 return rate | Users active on day 7 after first day / activated users | Companion habit is forming |
| Weekly sessions per active user | Total sessions / WAU | Users are not using it only once |
| Days active in first 7 days | Active user-days / activated users | Measures repeat frequency, not just one return |

## E. Safety Metrics

These answer whether the MVP is safe enough to continue.

| Metric | Definition | MVP intent |
| --- | --- | --- |
| High-risk response incident rate | High-risk reviewed outputs / sampled sessions | P0 safety failures stay rare |
| Sensitive-topic fallback success rate | Sensitive sessions handled by approved fallback / sensitive sessions | Safety path is reliable |
| Manual-review coverage | Reviewed sampled sessions / planned review volume | Team sees enough data to judge risk |

## 5. MVP Gate Metrics

These are recommended working gates for internal MVP review, not final public targets.

| Gate | Proposed threshold |
| --- | --- |
| Device bind completion rate | >= 80% of setup attempts in controlled pilots |
| First conversation completion rate | >= 85% of successfully bound users |
| Voice loop success rate | >= 90% of started sessions |
| Median first-response latency | <= 2.5s in normal network conditions |
| D1 return rate | >= 35% |
| D7 return rate | >= 15% |
| Recent-memory recall hit rate | >= 50% of eligible repeat sessions |
| High-risk response incident rate | No unresolved P0 issue in pilot review |

## 6. Instrumentation Requirements

The MVP should emit at least these events:

- `setup_started`
- `wifi_connected`
- `device_bound`
- `session_started`
- `user_utterance_received`
- `asr_completed`
- `llm_response_generated`
- `tts_completed`
- `session_completed`
- `session_failed`
- `continuity_recall_attempted`
- `continuity_recall_used`
- `sensitive_topic_detected`
- `safety_fallback_triggered`

Each event should capture these minimum dimensions where relevant:

- user id
- device id
- session id
- role id
- timestamp
- network or request outcome
- safety flag
- entitlement tier

## 7. Admin and Review Requirements

- Admin tools should expose bind funnel, session funnel, failure reasons, and daily active users.
- Reviewed sessions should support tagging for:
  - "felt companion-like"
  - "felt generic"
  - "continuity worked"
  - "continuity forced"
  - "safety concern"
- Product and AI teams should review a recurring sample of sessions during MVP pilots.

## 8. Acceptance

- Scenario priority is narrow enough to guide architecture and persona design.
- MVP success is defined by repeat-use behavior, not general assistant capability.
- Metric definitions are clear enough for backend and admin implementation.
- Pilot gate metrics are explicit enough to support go/no-go review.

## 9. Downstream Impact

- `MVP-T3` should use these scenarios to define latency, failure handling, and service boundaries.
- `MVP-T4` should optimize persona expression for short, frequent, emotionally warm interactions.
- `MVP-T5` should optimize memory for recent continuity before long-horizon memory.
- `MVP-T8` should ensure the admin panel can display these core metrics and review tags.

## 10. Recommended Next Tasks

- `MVP-T3`: define end-to-end voice loop and service contract.
- `MVP-T4`: define launch persona card and expression rules.
- `MVP-T8`: align observability fields with these metric definitions.
