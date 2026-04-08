const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export type EntitlementTier = "free" | "subscribed";
export type BindStatus = "unbound" | "bound";

export interface Account {
  accountId: string;
  authSubject: string;
  displayName: string | null;
  defaultRoleId: string;
  entitlementTier: EntitlementTier;
  createdAt: string;
}

export interface BindingRecord {
  bindingId: string;
  accountId: string;
  deviceId: string;
  status: BindStatus;
  boundAt: string;
  unboundAt: string | null;
}

export interface EntitlementSnapshot {
  accountId: string;
  tier: EntitlementTier;
  features: {
    voiceSession: boolean;
    recentContinuityMemory: boolean;
    priorityGeneration: boolean;
  };
}

export interface ErrorResponse {
  code: string;
  message: string;
}

export class ApiRequestError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
  }
}

async function parseBody(response: Response) {
  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  accountId?: string,
): Promise<T> {
  const headers = new Headers(options.headers);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (accountId) {
    headers.set("X-Account-Id", accountId);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
  const payload = await parseBody(response);

  if (!response.ok) {
    if (payload && typeof payload === "object" && "code" in payload && "message" in payload) {
      const errorPayload = payload as ErrorResponse;
      throw new ApiRequestError(response.status, errorPayload.code, errorPayload.message);
    }

    throw new ApiRequestError(response.status, "HTTP_ERROR", `Request failed with status ${response.status}.`);
  }

  return payload as T;
}

export function createAccount(payload: { authSubject: string; displayName?: string }) {
  return request<Account>("/v1/accounts", {
    method: "POST",
    body: JSON.stringify({
      authSubject: payload.authSubject,
      ...(payload.displayName ? { displayName: payload.displayName } : {}),
    }),
  });
}

export function getAccountMe(accountId: string) {
  return request<Account>("/v1/accounts/me", undefined, accountId);
}

export function bindDevice(accountId: string, pairingCode: string) {
  return request<BindingRecord>(
    "/v1/device-bindings",
    {
      method: "POST",
      body: JSON.stringify({ pairingCode }),
    },
    accountId,
  );
}

export function unbindDevice(accountId: string, deviceId: string) {
  return request<void>(
    `/v1/device-bindings/${deviceId}`,
    {
      method: "DELETE",
    },
    accountId,
  );
}

export function getEntitlement(accountId: string) {
  return request<EntitlementSnapshot>("/v1/entitlements/me", undefined, accountId);
}
