# MVP Baseline Acceptance

## Document Status

- Review mode only
- No new feature expansion
- Last updated: 2026-04-08

## Control Decision

Current MVP baseline decision:

- Python/backend/AI/firmware-simulator baseline: `PASS`
- User web build check: `BLOCKED_BY_LOCAL_ENV`
- Admin console build check: `BLOCKED_BY_LOCAL_ENV`
- Overall baseline freeze: `PASS_WITH_ENV_FOLLOW_UP`

The frontend build checks did not complete because the local machine does not have Node/npm available. This is an environment blocker, not evidence of a frontend or admin-console code failure.

## Python Baseline Verification

Command:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Result:

- `Ran 74 tests`
- `OK`

Notes:

- Intermediate `LLM provider failed`, `TTS provider failed`, and `memory provider failed` tracebacks are expected fallback-test logs.
- The final unittest result is successful.

Conclusion:

- Backend, AI orchestration, and firmware-simulator baseline verification is accepted.

## User Web Build Check

Commands attempted:

```bash
cd /Users/mac/Desktop/Ai-pet/apps/user-web
npm install
npm run build
```

Result:

- Not completed.

Reason:

- Local `npm` is unavailable.
- Observed blocker: `zsh: command not found: npm`

Conclusion:

- Do not count this as a code failure.
- Re-run after Node/npm is installed on the verification machine.

## Admin Console Build Check

Commands attempted:

```bash
cd /Users/mac/Desktop/Ai-pet/apps/admin-console
npm install
npm run build
```

Result:

- Not completed.

Reason:

- Local `npm` is unavailable.
- Observed blocker: `zsh: command not found: npm`

Conclusion:

- Do not count this as a code failure.
- Re-run after Node/npm is installed on the verification machine.

## Follow-Up Checklist

- [x] Record Python/backend/AI/firmware-simulator baseline as passing
- [x] Record frontend build checks as blocked by local Node/npm environment
- [x] Clarify that frontend build non-execution is not a code failure
- [ ] Install or provide Node/npm on a verification machine
- [ ] Re-run `apps/user-web` install/build check
- [ ] Re-run `apps/admin-console` install/build check

## Final Summary

The current MVP baseline can proceed. Python/backend/AI/firmware-simulator validation passed. Web and admin build verification remains a follow-up item blocked by local Node/npm availability and does not block the current MVP baseline freeze or forward progress.
