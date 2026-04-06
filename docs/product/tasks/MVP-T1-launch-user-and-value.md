# MVP-T1 Freeze Launch User and Value Proposition

## Task Metadata

| Field | Value |
| --- | --- |
| Task ID | MVP-T1 |
| Title | Freeze launch user and value proposition |
| Primary module | Product |
| Related modules | Persona, Safety, Subscription, AI Orchestration |
| Type | product |
| Priority | P0 |
| Branch suggestion | `docs/mvp-t1-launch-user-value` |
| Merge rule | Documentation-only, can merge to `main` after review |
| Status | done |

## 1. Decision Summary

- Launch line: young adults, not children.
- Launch age focus: 18-28.
- Primary user profile: students and early-career users who want a low-pressure, always-available emotional companion.
- Product promise: not "answer questions better," but "be a familiar companion that remembers you and keeps the relationship going."

## 2. Why This User Segment

### Chosen segment

- Users old enough to avoid child-compliance complexity in the first launch.
- Users more likely to accept habit-based companionship.
- Users more likely to tolerate early hardware imperfections if emotional value is strong.
- Users more likely to understand subscription value tied to continuity and memory.

### Not chosen for launch

- Children:
  requires guardian system, stronger content constraints, time limits, and dedicated review flows.
- Broad all-age route:
  would blur persona tone, safety policy, and subscription design.

## 3. Core Value Proposition

### Product statement

- A voice-based AI companion that users can talk to every day through dedicated hardware, with a stable personality, emotional continuity, and memory of the relationship.

### User-facing value

- It is easy to start: pick up the device and talk.
- It feels familiar: the companion has a stable personality.
- It remembers: conversations are not reset every day.
- It stays with the user: the relationship has continuity instead of feeling stateless.

### Not the core value

- General productivity assistant.
- Search engine replacement.
- Smart home control hub.
- Children's educational tutor.

## 4. Launch Scenario Focus

The MVP should focus on these scenarios first:

- End-of-day emotional decompression.
- Casual companionship when alone.
- Lightweight daily check-in.
- Ongoing follow-up on topics the user mentioned before.

The MVP should not prioritize these scenarios:

- Deep therapy claims.
- Educational coaching for children.
- Long-form task execution.
- Multi-user household sharing.

## 5. Free vs Subscription Boundary

## Free Tier

### Goal

- Let users feel the character, the voice interaction loop, and basic continuity.

### Includes

- Basic daily conversations.
- Fixed default role.
- Short continuity memory over recent interactions.
- Standard voice quality and standard response priority.

### Limits

- Limited depth of remembered history.
- Limited relationship continuity across longer time spans.
- No premium memory recall behaviors.
- Lower priority when system capacity is constrained.

## Subscription Tier

### Goal

- Sell a stronger feeling of "this companion knows me and our relationship continues."

### Includes

- Longer memory horizon.
- Better recall of preferences, past events, and relationship milestones.
- Stronger continuity across days and weeks.
- Better voice quality and/or faster response path if technically feasible.
- Priority access to new role features when available.

### Should not be paywalled

- Basic safety.
- Basic usability.
- The ability to have a normal conversation at all.

## 6. Persona Implications

- The launch persona should feel warm, calm, and emotionally available.
- The persona should not imitate a licensed IP, a real person, or a therapist.
- The persona should support repeatable daily interaction, not only novelty.
- The persona should be designed for trust and continuity, not dominance or dependency escalation.

## 7. Safety Implications

- Youth route is intentionally excluded from MVP launch scope.
- The system should avoid presenting itself as a medical or mental-health professional.
- Emotional support is in scope; therapeutic claims are out of scope.
- Sensitive topics require fallback handling and reviewability from day one.

## 8. Downstream Impact

This decision directly shapes the next MVP tasks:

- `MVP-T2` should define metrics around repeat usage, session quality, and 7-day return.
- `MVP-T3` should optimize for low-friction voice companionship, not broad assistant capabilities.
- `MVP-T4` should define one launch role card for daily emotional companionship.
- `MVP-T5` should keep memory lightweight but continuity-focused.
- `V1-T1` should package long-term continuity as the main subscription value.

## 9. Acceptance

- Launch user segment is narrowed enough to guide role, safety, and subscription design.
- Core product promise is clear and does not drift into generic assistant scope.
- Free vs paid boundary is clear enough for MVP and V1 planning.
- Child route is explicitly deferred into a separate future workstream.

## 10. Recommended Next Tasks

- `MVP-T2`: define success metrics and core usage scenarios.
- `MVP-T3`: define end-to-end voice loop and service boundary.
- `MVP-T4`: define launch persona card and expression rules.
