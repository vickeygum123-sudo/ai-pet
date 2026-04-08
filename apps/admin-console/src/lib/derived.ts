import type { Device, FailureCode, Session } from "./api";

export const failureCodes: FailureCode[] = [
  "AUTH_FAILED",
  "NETWORK_TIMEOUT",
  "ASR_FAILED",
  "CONTEXT_LOAD_FAILED",
  "LLM_TIMEOUT",
  "LLM_FAILED",
  "TTS_FAILED",
  "SAFETY_BLOCKED",
  "UNKNOWN_ERROR",
];

export const sessionStates = [
  "idle",
  "listening",
  "transcribing",
  "reasoning",
  "synthesizing",
  "speaking",
  "completed",
  "failed",
  "fallback",
] as const;

export function median(values: number[]) {
  if (values.length === 0) {
    return null;
  }

  const sorted = [...values].sort((left, right) => left - right);
  const midpoint = Math.floor(sorted.length / 2);

  if (sorted.length % 2 === 0) {
    return Math.round((sorted[midpoint - 1] + sorted[midpoint]) / 2);
  }

  return sorted[midpoint];
}

export function countOnlineDevices(devices: Device[]) {
  return devices.filter((device) => device.deviceStatus === "connected" || device.deviceStatus === "ready_to_speak").length;
}

export function getLatestLastOnlineAt(devices: Device[]) {
  return devices
    .map((device) => device.lastOnlineAt)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1) ?? null;
}

export function firmwareDistribution(devices: Device[]) {
  const counts = new Map<string, number>();

  devices.forEach((device) => {
    counts.set(device.firmwareVersion, (counts.get(device.firmwareVersion) ?? 0) + 1);
  });

  return Array.from(counts.entries())
    .map(([firmwareVersion, count]) => ({ firmwareVersion, count }))
    .sort((left, right) => right.count - left.count);
}

export function sessionSuccessRate(sessions: Session[]) {
  if (sessions.length === 0) {
    return null;
  }

  const completedCount = sessions.filter((session) => session.state === "completed").length;
  return Math.round((completedCount / sessions.length) * 100);
}

export function medianFirstResponseLatency(sessions: Session[]) {
  return median(
    sessions
      .map((session) => session.firstResponseLatencyMs)
      .filter((value): value is number => typeof value === "number"),
  );
}

export function failureBreakdown(sessions: Session[]) {
  const counts = new Map<string, number>();

  sessions.forEach((session) => {
    const key = session.failureCode ?? "NO_FAILURE_CODE";
    counts.set(key, (counts.get(key) ?? 0) + 1);
  });

  return Array.from(counts.entries())
    .map(([code, count]) => ({ code, count }))
    .sort((left, right) => right.count - left.count);
}

export function statusBreakdown(sessions: Session[]) {
  const counts = new Map<string, number>();

  sessions.forEach((session) => {
    counts.set(session.state, (counts.get(session.state) ?? 0) + 1);
  });

  return Array.from(counts.entries())
    .map(([state, count]) => ({ state, count }))
    .sort((left, right) => right.count - left.count);
}

export function continuityStats(sessions: Session[]) {
  const continuityUsed = sessions.filter((session) => session.continuityRecallUsed).length;
  return {
    continuityUsed,
    repeatUserSessions: new Set(sessions.map((session) => session.accountId)).size,
  };
}

export function safetyStats(sessions: Session[]) {
  return {
    safetyFlagged: sessions.filter((session) => session.safetyFlag).length,
    fallbackCount: sessions.filter((session) => session.fallbackUsed || session.state === "fallback").length,
    blockedOutputs: sessions.filter((session) => session.failureCode === "SAFETY_BLOCKED").length,
  };
}

export function reviewCandidates(sessions: Session[]) {
  return sessions.filter(
    (session) =>
      session.safetyFlag ||
      session.fallbackUsed ||
      session.state === "fallback" ||
      session.failureCode === "SAFETY_BLOCKED",
  );
}
