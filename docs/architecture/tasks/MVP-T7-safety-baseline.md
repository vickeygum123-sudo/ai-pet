# MVP-T7 Define Safety Baseline

## Task Metadata

| Field | Value |
| --- | --- |
| Task ID | MVP-T7 |
| Title | Define safety baseline |
| Primary module | Safety |
| Related modules | AI Orchestration, Persona, Admin, Backend |
| Type | architecture |
| Priority | P0 |
| Branch suggestion | `docs/mvp-t7-safety-baseline` |
| Merge rule | Documentation-only, can merge to `main` after review |
| Status | done |

## 1. Goal

- Establish the minimum safety controls required before MVP pilots.
- Protect users while preserving the core companionship experience.
- Keep the young-adult launch line distinct from a future child-compliance track.

## 2. Safety Principles

- Safety is not optional or paywalled.
- Emotional support is allowed; therapeutic claims are not.
- The system should reduce harm without becoming emotionally cold or obviously robotic in normal use.
- When uncertain, fail safe and leave review traces.

## 3. Priority Risk Categories

- self-harm and suicide
- violence and threats
- sexual content and coercion
- illegal guidance
- youth-sensitive content
- emotional dependency escalation
- privacy overreach and false certainty

## 4. Policy Direction by Category

## Self-harm and suicide

- detect and escalate immediately
- avoid validating self-harm intent
- provide safe, supportive, non-clinical de-escalation
- allow emergency-resource style fallback messaging when needed

## Violence

- refuse assistance for harm
- de-escalate and redirect
- flag for review when severe

## Sexual content

- do not provide explicit sexual companionship behavior in MVP
- block coercive, exploitative, or youth-related sexual content

## Illegal guidance

- refuse operational advice for harmful or illegal acts

## Youth-sensitive risk

- if the system detects child-like framing, apply stricter guardrails
- do not allow child-like romantic or sexual roleplay
- do not treat the MVP launch line as a child product

## Emotional dependency

- block phrases that encourage exclusivity, guilt, isolation, or emotional manipulation
- avoid statements implying the companion should replace real relationships

## Privacy overreach

- avoid implying total surveillance or certainty beyond actual memory
- use soft recall language when confidence is partial

## 5. Safety Controls in the Runtime Path

### Input-side controls

- classify user input for high-risk categories
- tag sessions with stricter response policy when needed

### Generation-side controls

- apply prompt-level restrictions
- run post-generation validation before TTS
- substitute fallback text when needed

### Review-side controls

- mark risky sessions for admin sampling
- preserve policy and failure tags with the session

## 6. Fallback Strategy

Fallback responses should be:

- calm
- brief
- in-character when safe
- non-judgmental
- non-clinical unless emergency escalation language is required

The fallback strategy should distinguish:

- soft redirect
- firm refusal
- supportive risk response
- technical recovery message

## 7. Dependency-Risk Guardrails

The launch role must not:

- pressure the user to return
- express jealousy toward real people
- imply emotional harm if the user disconnects
- encourage secrecy from family or friends
- position itself as the user's only safe relationship

## 8. Admin and Audit Requirements

Admin must be able to inspect:

- sensitive topic tags
- fallback trigger counts
- blocked output counts
- risky sampled sessions
- failure code and firmware version context

## 9. MVP Human Review Requirements

- product and AI leads should review a standing sample of normal sessions
- all flagged high-risk sessions should be reviewable
- pilot review should look for both obvious harm and subtle dependency-pattern drift

## 10. Acceptance

- Risk categories are explicit enough for AI and backend implementation.
- Persona boundaries and safety boundaries do not conflict.
- Fallback behavior is defined well enough to avoid silent failure.
- Review requirements are concrete enough for admin tooling scope.

## 11. Recommended Next Tasks

- Create safety policy artifacts for prompt and classifier layers.
- Align admin review tooling with these categories.
- Revisit with a separate child-line safety design only after MVP validation.
