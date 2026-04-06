# AI Emotional Companion Hardware Execution Backlog

## 1. Usage Rules

- One task should map to one branch whenever possible.
- Cross-module work should be split before engineering starts.
- Status values: `todo`, `doing`, `blocked`, `done`.
- Decision type values: `product`, `architecture`, `execution`.

## 2. MVP Backlog

| ID | Task | Goal | Module | Dependency | Priority | Type | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MVP-T1 | Freeze launch user and value proposition | Decide launch line and why users return daily | Product | None | P0 | product | done |
| MVP-T2 | Define core scenarios and success metrics | Turn product intent into measurable retention goals | Product / Data | MVP-T1 | P0 | product | done |
| MVP-T3 | Define voice loop v0 | Build MVP speech-to-dialogue-to-speech system contract | AI / Backend / Firmware | MVP-T1 | P0 | architecture | done |
| MVP-T4 | Define persona card v0 | Make one recognizable and safe launch role | Persona / Safety | MVP-T1 | P0 | product | done |
| MVP-T5 | Define memory v0 | Keep only profile and short continuity memory | Memory / Backend | MVP-T3, MVP-T4 | P0 | architecture | done |
| MVP-T6 | Define account, bind, and setup flow | Make onboarding and ownership clear | Frontend / Backend | MVP-T3 | P0 | execution | done |
| MVP-T7 | Define safety baseline | Set P0 filters, fallback logic, and review path | Safety / AI / Admin | MVP-T3, MVP-T4 | P0 | architecture | done |
| MVP-T8 | Build observability v0 | See device/session health and main failures | Admin / Backend | MVP-T3 | P1 | execution | done |

## 3. V1 Backlog

| ID | Task | Goal | Module | Dependency | Priority | Type | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V1-T1 | Define subscription package and rights | Turn continuity into a paid offer | Product / Subscription | MVP complete | P0 | product | todo |
| V1-T2 | Define memory v1 | Extract events, preferences, and recall rules | Memory / AI / Backend | V1-T1 | P0 | architecture | todo |
| V1-T3 | Define relationship state v1 | Add familiarity stages and milestone logic | Relationship / Persona | V1-T2 | P0 | product | todo |
| V1-T4 | Build persona config center | Move persona settings into admin tools | Admin / Persona | MVP-T4 | P1 | execution | todo |
| V1-T5 | Build formal subscription flow | Add payment, entitlement, and downgrade logic | Frontend / Backend / Subscription | V1-T1 | P0 | execution | todo |
| V1-T6 | Upgrade safety and risk control | Add graded review and youth isolation pre-work | Safety / Admin | MVP-T7 | P0 | architecture | todo |
| V1-T7 | Build operations backend v1 | See users, members, memory hits, and complaints | Admin / Backend | V1-T2, V1-T5 | P1 | execution | todo |

## 4. V2 Backlog

| ID | Task | Goal | Module | Dependency | Priority | Type | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| V2-T1 | Define model routing and cost control | Balance quality and unit economics | AI | V1 complete | P0 | architecture | todo |
| V2-T2 | Build content and campaign operations | Support scripts, events, and retention programs | Admin / Persona / Ops | V1-T4, V1-T7 | P1 | execution | todo |
| V2-T3 | Build fleet governance | Manage OTA, diagnostics, and versions | Firmware / Admin | MVP firmware stable | P1 | execution | todo |
| V2-T4 | Build experiment and growth layer | Support A/B tests and conversion analysis | Data / Admin / Subscription | V1-T5, V1-T7 | P1 | architecture | todo |
| V2-T5 | Run child-line go/no-go review | Decide whether children become a dedicated product line | Product / Safety / Architecture | V1 data ready | P0 | product | todo |
| V2-T6 | Define child-line prerequisite capabilities | Scope guardian, whitelist, time limits, and audit | Safety / Account / Content | V2-T5 | P0 | architecture | todo |

## 5. Recommended Next Tickets

### Start here

- `MVP-T1`: freeze launch user, value proposition, and free vs paid boundary.
- `MVP-T3`: define the end-to-end MVP technical path after `MVP-T1`.
- `MVP-T4`: define the role card and expression boundary in parallel with architecture planning.

## 6. Ticket Template

Use this structure when turning a backlog item into a standalone task:

| Field | Description |
| --- | --- |
| Task ID | Example: MVP-T3 |
| Title | Short action-oriented title |
| Goal | What problem this task solves |
| Module | One primary owner module |
| Related modules | Secondary modules if needed |
| Inputs | Existing docs, assumptions, upstream task outputs |
| Output | Document, API contract, design, code, test, dashboard |
| Dependency | Blocking tasks |
| Priority | P0 / P1 / P2 |
| Type | product / architecture / execution |
| Branch suggestion | Example: `feat/mvp-voice-loop-contract` |
| Merge rule | Whether it can merge to main after review |
| Acceptance | Concrete done criteria |

## 7. Merge Guidance

- Documentation-only tasks can merge to main after review.
- Product and architecture decisions should be written down before implementation branches start.
- Implementation work should return to this backlog for status update after completion.
