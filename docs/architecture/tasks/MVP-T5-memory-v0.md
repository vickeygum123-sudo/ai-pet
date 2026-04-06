# MVP-T5 Define Memory v0

## Task Metadata

| Field | Value |
| --- | --- |
| Task ID | MVP-T5 |
| Title | Define memory v0 |
| Primary module | Memory |
| Related modules | Backend, AI Orchestration, Persona |
| Type | architecture |
| Priority | P0 |
| Branch suggestion | `docs/mvp-t5-memory-v0` |
| Merge rule | Documentation-only, can merge to `main` after review |
| Status | done |

## 1. Goal

- Support the MVP promise of short-term continuity without building a heavy long-term memory system.
- Keep memory simple, cheap, reviewable, and low-risk.
- Optimize for recent relevance instead of historical completeness.

## 2. Memory v0 Scope

### In scope

- user profile basics
- recent conversation continuity
- lightweight stable preferences that improve companionship
- manual or programmatic memory disable on failure

### Out of scope

- full life history graph
- semantic knowledge base for each user
- deep emotional trait inference
- autonomous long-term planning
- complex user-editable memory UI

## 3. Memory Layers

## A. User Profile Memory

Stores slow-changing facts that help the role feel familiar.

Examples:

- preferred name
- pronouns if provided
- broad routine hints
- broad likes and dislikes

## B. Recent Continuity Memory

Stores recent conversational items that are likely to matter in the next few interactions.

Examples:

- an interview tomorrow
- a conflict with a friend
- a stressful week
- a plan to exercise again

## C. Relationship Markers

Stores minimal relationship continuity metadata.

Examples:

- first conversation timestamp
- recent active days
- last notable topic

## 4. Storage Schema v0

### Minimum user profile fields

- user id
- preferred display name
- pronoun preference
- stable preferences list
- updated at

### Minimum continuity item fields

- memory id
- user id
- session id source
- memory type
- summary text
- confidence
- created at
- expiry at
- last used at
- status

### Minimum relationship fields

- user id
- first seen at
- last active at
- total sessions
- recent streak proxy
- last continuity topic

## 5. Memory Types v0

- `profile_preference`
- `profile_identity`
- `recent_topic`
- `recent_emotional_context`
- `relationship_marker`

## 6. Write Rules

- Not every session should create memory.
- Memory writes should happen only when the extracted item is:
  - useful
  - recent enough to matter
  - safe to retain
  - above a confidence threshold

### Good write examples

- "User has an interview tomorrow."
- "User prefers being called Mia."
- "User felt anxious about finals this week."

### Bad write examples

- trivial filler from casual chatter
- speculative personality diagnosis
- highly sensitive data without a clear product reason
- anything likely to create a creepy feeling if recalled

## 7. Recall Rules

- Prefer at most 1-2 recalled items in a single response context.
- Prefer recent items over older ones.
- Prefer high-confidence items over broad low-confidence recall.
- Prefer topic-continuation items over generic profile recall.
- Do not block the conversation if no memory is found.

## 8. Expiry Rules

- recent topic memory should expire quickly by default
- emotional context memory should decay unless reinforced
- stable profile preferences can live longer
- relationship markers persist longer than recent topical memory

Suggested MVP defaults:

- `recent_topic`: 7 days
- `recent_emotional_context`: 3-7 days depending on confidence
- `profile_preference`: 90 days or until corrected
- `relationship_marker`: persistent unless deleted

## 9. Safety and Privacy Guardrails

- Do not store raw full transcripts as memory v0 source of truth.
- Store short structured summaries instead.
- Avoid retaining highly sensitive content unless explicitly required by safety or compliance handling.
- Memory recall should be suppressible for flagged sessions.

## 10. Runtime Integration

### Read path

1. Orchestrator receives normalized utterance.
2. Memory service checks for recent relevant continuity items.
3. At most 1-2 top items are returned.
4. Prompt builder injects soft continuity context.

### Write path

1. Session completes.
2. Extractor proposes candidate memory items.
3. Rules filter low-value or unsafe candidates.
4. Approved items are written asynchronously.

## 11. Failure Handling

- If memory read fails, continue without memory.
- If memory write fails, session still succeeds.
- If recall confidence is low, suppress recall instead of guessing.
- If a memory item is marked unsafe or disputed, exclude it from prompts immediately.

## 12. Acceptance

- Memory scope is narrow enough for MVP latency and cost goals.
- Schema is clear enough for backend and orchestrator implementation.
- Recall policy supports continuity without creating a surveillance feeling.
- Failure behavior is safe and does not block core conversation flow.

## 13. Recommended Next Tasks

- Implement memory read/write contract inside orchestration path.
- Define review and deletion hooks before V1 memory expansion.
- Keep V1 memory design separate from this MVP memory scope.
