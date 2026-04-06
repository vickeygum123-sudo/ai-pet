# MVP-T6 Define Account, Bind, and Setup Flow

## Task Metadata

| Field | Value |
| --- | --- |
| Task ID | MVP-T6 |
| Title | Define account, bind, and setup flow |
| Primary module | Frontend |
| Related modules | Backend, Firmware, Account |
| Type | execution |
| Priority | P0 |
| Branch suggestion | `docs/mvp-t6-setup-bind-flow` |
| Merge rule | Documentation-only, can merge to `main` after review |
| Status | done |

## 1. Goal

- Make the first-time setup path short enough that users reach first conversation with minimal friction.
- Keep account, device ownership, and role assignment clear from day one.

## 2. MVP Setup Flow

### Step 1: Unbox and power on

- Device enters pairing-ready state.
- User sees pairing cue from device and packaging instructions.

### Step 2: Web onboarding entry

- User opens setup page by QR code or printed URL.
- User signs in or creates an account.

### Step 3: Device pairing and Wi-Fi setup

- Web page discovers or guides the user to connect the device.
- User provides Wi-Fi credentials.
- Device confirms cloud connectivity.

### Step 4: Device binding

- Backend binds device id to account id.
- User sees ownership confirmation.

### Step 5: Basic role confirmation

- User sees the launch companion description.
- User may set a display name or basic preference if desired.
- Do not introduce full role marketplace in MVP.

### Step 6: First conversation

- User receives a clear prompt to talk to the device.
- The first conversation should happen immediately after successful bind.

## 3. Required Surfaces

### User web

- sign in / sign up
- device setup landing
- Wi-Fi setup flow
- bind success page
- simple account page
- simple device page

### Firmware states exposed to user

- ready to pair
- connecting
- connected
- failed to connect
- ready to speak

## 4. Backend Ownership

- account creation and login
- device registration
- bind and unbind rules
- device ownership lookup
- first-role assignment
- setup funnel event collection

## 5. MVP Data Objects

### Account

- account id
- auth identity
- created at
- subscription tier

### Device

- device id
- firmware version
- hardware model
- bind state
- owner account id
- last online at

### Binding record

- bind id
- account id
- device id
- bound at
- unbound at
- status

## 6. UX Rules

- Setup must minimize form filling.
- Users should not need to understand the backend model.
- Wi-Fi and bind errors must be translated into plain language.
- The user should always know whether the problem is network, account, or device related.

## 7. Error Cases

- Wi-Fi credentials invalid
- device cannot reach cloud
- device already bound
- auth session expired
- bind token invalid
- setup timeout

For MVP, every error should map to:

- short user-facing explanation
- retry action
- backend failure code for support and admin use

## 8. Integration with Metrics

This flow must emit:

- `setup_started`
- `account_created`
- `device_detected`
- `wifi_config_submitted`
- `wifi_connected`
- `device_bound`
- `setup_failed`
- `first_conversation_started`

## 9. Acceptance

- Setup path is simple enough to support pilot users without manual team intervention in most cases.
- Ownership model is clear enough for backend and support handling.
- Error states are explicit enough for frontend and firmware implementation.
- The first conversation is part of setup completion, not a separate later flow.

## 10. Recommended Next Tasks

- Frontend topic: turn this into onboarding screens and account flows.
- Backend topic: define bind APIs and ownership rules.
- Firmware topic: expose setup states and cloud-connect callbacks.
