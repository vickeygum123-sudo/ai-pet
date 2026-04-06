# A2 failureCode Null Compatibility Checklist

## Document Status

- Review mode only
- No new feature expansion
- Last updated: 2026-04-06

## Purpose

This checklist verifies whether the updated `failureCode = null` semantics affect existing callers.

The semantics after the fix are:

1. `session.failureCode` reflects the latest persisted outcome of the session.
2. On a successful latest run, `session.failureCode = null`.
3. `runtimeFailureCode` remains the current-request runtime outcome.
4. For `PATCH /v1/device-sessions/{sessionId}`:
   - omit `failureCode`: keep previous value unchanged
   - send `failureCode: null`: explicitly clear it

## Compatibility Risk Summary

Overall assessment:

- Low to medium risk for display and analytics callers
- Low risk for firmware runtime behavior
- Medium risk only for any caller that incorrectly treated `session.failureCode` as a sticky historical field

Current repository scan did not find any caller that requires `session.failureCode` to remain historically sticky.

## Caller Matrix

| Caller / Area | File | Current usage | Impact from `failureCode = null` | Review result |
| --- | --- | --- | --- | --- |
| Admin API typed session model | [/Users/mac/Desktop/Ai-pet/apps/admin-console/src/lib/api.ts](/Users/mac/Desktop/Ai-pet/apps/admin-console/src/lib/api.ts) | `failureCode: FailureCode \| null` already nullable | none | pass |
| Session detail page | [/Users/mac/Desktop/Ai-pet/apps/admin-console/src/pages/SessionDetailPage.tsx](/Users/mac/Desktop/Ai-pet/apps/admin-console/src/pages/SessionDetailPage.tsx) | uses `formatNullableText(session.failureCode)` | null already supported and displayed | pass |
| Session list page | [/Users/mac/Desktop/Ai-pet/apps/admin-console/src/pages/SessionsPage.tsx](/Users/mac/Desktop/Ai-pet/apps/admin-console/src/pages/SessionsPage.tsx) | displays `session.failureCode`, filters only non-null codes | no breakage; cannot filter null, but this was already true | pass with note |
| Failure breakdown page | [/Users/mac/Desktop/Ai-pet/apps/admin-console/src/pages/FailuresPage.tsx](/Users/mac/Desktop/Ai-pet/apps/admin-console/src/pages/FailuresPage.tsx) | groups null as `NO_FAILURE_CODE` | compatible and useful after fix | pass |
| Derived admin aggregations | [/Users/mac/Desktop/Ai-pet/apps/admin-console/src/lib/derived.ts](/Users/mac/Desktop/Ai-pet/apps/admin-console/src/lib/derived.ts) | `failureBreakdown`, `blockedOutputs`, `reviewCandidates` | null-safe logic already exists | pass |
| Review queue | [/Users/mac/Desktop/Ai-pet/apps/admin-console/src/pages/ReviewQueuePage.tsx](/Users/mac/Desktop/Ai-pet/apps/admin-console/src/pages/ReviewQueuePage.tsx) | only special-cases `SAFETY_BLOCKED`; also uses `fallbackUsed` and `state` | null does not remove valid review candidates because fallback/state remain available | pass |
| Overview safety cards | [/Users/mac/Desktop/Ai-pet/apps/admin-console/src/pages/OverviewPage.tsx](/Users/mac/Desktop/Ai-pet/apps/admin-console/src/pages/OverviewPage.tsx) | blocked outputs use `failureCode === SAFETY_BLOCKED` | unchanged; successful reruns should no longer inflate failure counts | pass |
| Firmware runtime adapter | [/Users/mac/Desktop/Ai-pet/src/firmware/cloud.py](/Users/mac/Desktop/Ai-pet/src/firmware/cloud.py) | reads `runtimeFailureCode`, not `session.failureCode` | unaffected | pass |
| Firmware response model | [/Users/mac/Desktop/Ai-pet/src/firmware/models.py](/Users/mac/Desktop/Ai-pet/src/firmware/models.py) | no `session.failureCode` field | unaffected | pass |
| User web | [/Users/mac/Desktop/Ai-pet/apps/user-web/src/lib/api.ts](/Users/mac/Desktop/Ai-pet/apps/user-web/src/lib/api.ts) | no session consumption | unaffected | pass |
| Voice-loop integration | [/Users/mac/Desktop/Ai-pet/src/backend_foundation/voice_loop_integration.py](/Users/mac/Desktop/Ai-pet/src/backend_foundation/voice_loop_integration.py) | passes mapped backend failure code to session update | now correctly clears stale value on success | pass |
| Session service layers | [/Users/mac/Desktop/Ai-pet/src/backend_foundation/application.py](/Users/mac/Desktop/Ai-pet/src/backend_foundation/application.py), [/Users/mac/Desktop/Ai-pet/src/backend_foundation/service.py](/Users/mac/Desktop/Ai-pet/src/backend_foundation/service.py) | persistence/update logic | explicitly supports clear vs keep semantics | pass |
| PATCH session API | [/Users/mac/Desktop/Ai-pet/src/backend_foundation/api/app.py](/Users/mac/Desktop/Ai-pet/src/backend_foundation/api/app.py) | manual update path | callers must understand omit vs null semantics | pass with note |

## Detailed Checks

### 1. Golden Path display impact

Expected after fix:

- successful latest session shows `failureCode = null`
- admin pages render that as empty/null-safe text or `NO_FAILURE_CODE`

Result:

- no code break found in current repo consumers

### 2. Failure-path analytics impact

Expected after fix:

- failed sessions still retain concrete `failureCode`
- successful reruns no longer pollute breakdown counts

Result:

- this is a positive correction
- admin aggregated charts and tables should become more accurate, not less

### 3. Review queue impact

Risk:

- if review selection depended only on old sticky `failureCode`, some sessions might disappear from queue after a successful rerun

Current logic:

- review queue also uses `fallbackUsed`, `state === "fallback"`, and `safetyFlag`

Result:

- no immediate break found
- behavior is more aligned with “current latest session state” semantics

### 4. Firmware impact

Risk:

- firmware might read `session.failureCode` and infer current failure

Current logic:

- firmware adapter reads `runtimeFailureCode` and `session.state`

Result:

- no impact

### 5. PATCH API semantic impact

New rule:

- omitted `failureCode` means “leave unchanged”
- explicit `null` means “clear failure code”

Risk:

- a future caller may assume `null` and omission are identical

Current repo status:

- no app or firmware caller currently uses `PATCH /v1/device-sessions/{sessionId}`

Result:

- no active caller break found
- this semantic must be documented for future callers

## Required Manual Verification

### Admin Console

- [ ] Session detail page shows empty/null-safe value for successful rerun
- [ ] Failures page groups successful rerun under `NO_FAILURE_CODE`
- [ ] Sessions list renders successful rerun without stale `LLM_FAILED`
- [ ] Review queue still includes safety fallback sessions as expected

### Real Runtime

- [ ] Run one real `LLM_FAILED` or fallback sample if feasible
- [ ] Run one successful real Golden Path on the same session or a fresh session
- [ ] Confirm latest successful response returns:
  - `session.state = completed`
  - `session.failureCode = null`
  - `runtimeFailureCode = none`
  - `fallbackUsed = false`

### Security Exception / Ops-Release Readiness

- [ ] Rotate the exposed DeepSeek key
- [ ] Reconfigure runtime with the replacement key
- [ ] Run one post-rotation real Golden Path retest before release readiness sign-off

## Notes for Reviewers

1. `session.failureCode` should no longer be interpreted as “historical latest error ever seen on this session id”.
2. `runtimeFailureCode` remains the correct field for current request outcome.
3. Analytics or dashboards that want historical failures should use transitions, event logs, or future dedicated metrics rather than sticky reuse of `session.failureCode`.
4. DeepSeek key rotation is a security follow-up and does not block the current MVP baseline freeze or A2 functional PASS.

## Final Checklist

- [x] repo callers using `failureCode` have been enumerated
- [x] firmware impact reviewed
- [x] admin-console impact reviewed
- [x] PATCH semantics documented
- [x] no active caller break found in repository scan
- [ ] manual UI smoke check completed
- [x] DeepSeek new-key retest is no longer treated as a functional blocker
- [ ] new DeepSeek key rotated
- [ ] post-rotation Golden Path retest completed for ops-release readiness
