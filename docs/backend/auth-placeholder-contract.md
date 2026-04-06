# Auth Placeholder Contract

## Version

- MVP

## Task ID

- `MVP-T3 / MVP-T6 / MVP-T8` backend-owned portion only

## Current Branch

- `feat/backend-device-session-foundation`

## Purpose

Document the current MVP auth placeholder so review can happen without confusing it for real auth integration.

## Current Placeholder Rule

Endpoints that operate on the authenticated account currently use:

- request header: `X-Account-Id`

This is a temporary backend-only placeholder for MVP development and review.

## Endpoints Using The Placeholder

- `GET /v1/accounts/me`
- `POST /v1/device-bindings`
- `DELETE /v1/device-bindings/{deviceId}`
- `GET /v1/entitlements/me`

## Placeholder Error Behavior

- missing header returns `401`
- error response body:

```json
{
  "code": "AUTH_HEADER_REQUIRED",
  "message": "Missing X-Account-Id header for MVP auth placeholder."
}
```

## What This Placeholder Is Good For

- repository and service verification
- API contract review
- frontend and admin mock integration

## What This Placeholder Must Not Be Mistaken For

- real user identity verification
- token validation
- permission model
- admin authorization
- device authentication

## Replacement Plan

When a real auth task starts later, it should:

1. introduce a real user token/session strategy
2. map token identity to `account_id`
3. preserve current route semantics wherever possible
4. remove `X-Account-Id` from user-facing integration guidance
