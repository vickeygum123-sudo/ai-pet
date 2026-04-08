export type SetupEventName =
  | "setup_started"
  | "account_created"
  | "wifi_config_submitted"
  | "device_bound"
  | "setup_failed";

export function trackSetupEvent(
  eventName: SetupEventName,
  payload: Record<string, string | number | boolean | undefined> = {},
) {
  if (import.meta.env.DEV) {
    console.info("[user-web telemetry stub]", eventName, payload);
  }
}
