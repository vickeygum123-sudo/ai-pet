const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

export type EntitlementTier = "free" | "subscribed";
export type BindStatus = "unbound" | "bound";
export type DeviceStatus =
  | "pairing_ready"
  | "connecting"
  | "connected"
  | "failed_to_connect"
  | "ready_to_speak"
  | "offline";
export type SessionState =
  | "idle"
  | "listening"
  | "transcribing"
  | "reasoning"
  | "synthesizing"
  | "speaking"
  | "completed"
  | "failed"
  | "fallback";
export type StepStatus = "pending" | "succeeded" | "failed" | "skipped";
export type FailureCode =
  | "AUTH_FAILED"
  | "NETWORK_TIMEOUT"
  | "ASR_FAILED"
  | "CONTEXT_LOAD_FAILED"
  | "LLM_TIMEOUT"
  | "LLM_FAILED"
  | "TTS_FAILED"
  | "SAFETY_BLOCKED"
  | "UNKNOWN_ERROR";

export interface ErrorResponse {
  code: string;
  message: string;
}

export interface AdminOverview {
  totalAccounts: number;
  totalDevices: number;
  boundDevices: number;
  activeSessions: number;
  completedSessions: number;
  failedSessions: number;
}

export interface Device {
  deviceId: string;
  hardwareModel: string;
  firmwareVersion: string;
  deviceStatus: DeviceStatus;
  bindStatus: BindStatus;
  ownerAccountId: string | null;
  pairingCode: string;
  lastOnlineAt: string | null;
  createdAt: string;
}

export interface SessionTransition {
  state: SessionState;
  recordedAt: string;
  notes: string | null;
}

export interface Session {
  sessionId: string;
  accountId: string;
  deviceId: string;
  roleId: string;
  entitlementTier: EntitlementTier;
  state: SessionState;
  asrStatus: StepStatus;
  llmStatus: StepStatus;
  ttsStatus: StepStatus;
  safetyFlag: boolean;
  fallbackUsed: boolean;
  continuityRecallUsed: boolean;
  firstResponseLatencyMs: number | null;
  failureCode: FailureCode | null;
  firmwareVersion: string;
  startedAt: string;
  endedAt: string | null;
  transitions: SessionTransition[];
}

interface DeviceListResponse {
  items: Device[];
}

interface SessionListResponse {
  items: Session[];
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

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
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

function toSearchParams(query: Record<string, string | undefined>) {
  const params = new URLSearchParams();

  Object.entries(query).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });

  const serialized = params.toString();
  return serialized ? `?${serialized}` : "";
}

export function getAdminOverview() {
  return request<AdminOverview>("/v1/admin/overview");
}

export function listAdminDevices(query: {
  bindStatus?: BindStatus | "";
  ownerAccountId?: string;
}) {
  return request<DeviceListResponse>(
    `/v1/admin/devices${toSearchParams({
      bindStatus: query.bindStatus || undefined,
      ownerAccountId: query.ownerAccountId?.trim() || undefined,
    })}`,
  ).then((response) => response.items);
}

export function listAdminSessions(query: {
  state?: SessionState | "";
  failureCode?: FailureCode | "";
  accountId?: string;
  deviceId?: string;
}) {
  return request<SessionListResponse>(
    `/v1/admin/sessions${toSearchParams({
      state: query.state || undefined,
      failureCode: query.failureCode || undefined,
      accountId: query.accountId?.trim() || undefined,
      deviceId: query.deviceId?.trim() || undefined,
    })}`,
  ).then((response) => response.items);
}

export function getAdminSessionDetail(sessionId: string) {
  return request<Session>(`/v1/admin/sessions/${sessionId}`);
}
