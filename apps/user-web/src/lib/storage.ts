import type { BindingRecord } from "./api";

const ACCOUNT_SESSION_KEY = "ai-pet.user-web.account-session";
const ONBOARDING_DRAFT_KEY = "ai-pet.user-web.onboarding-draft";
const BINDING_CACHE_KEY = "ai-pet.user-web.binding-cache";

export interface AccountSession {
  accountId: string;
  authMode: "placeholder-create" | "placeholder-login";
  createdAt: string;
}

export interface OnboardingDraft {
  wifiName: string;
  pairingCode: string;
  deviceNotes: string;
}

export interface BindingCache {
  binding: BindingRecord;
  pairingCode: string;
  wifiName: string;
  deviceNotes: string;
  cachedAt: string;
}

function readJson<T>(key: string): T | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.localStorage.getItem(key);

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function writeJson<T>(key: string, value: T) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(key, JSON.stringify(value));
}

function remove(key: string) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.removeItem(key);
}

export function getAccountSession() {
  return readJson<AccountSession>(ACCOUNT_SESSION_KEY);
}

export function setAccountSession(value: AccountSession) {
  writeJson(ACCOUNT_SESSION_KEY, value);
}

export function clearAccountSession() {
  remove(ACCOUNT_SESSION_KEY);
}

export function getOnboardingDraft() {
  return readJson<OnboardingDraft>(ONBOARDING_DRAFT_KEY);
}

export function setOnboardingDraft(value: OnboardingDraft) {
  writeJson(ONBOARDING_DRAFT_KEY, value);
}

export function clearOnboardingDraft() {
  remove(ONBOARDING_DRAFT_KEY);
}

export function getBindingCache() {
  return readJson<BindingCache>(BINDING_CACHE_KEY);
}

export function setBindingCache(value: BindingCache) {
  writeJson(BINDING_CACHE_KEY, value);
}

export function clearBindingCache() {
  remove(BINDING_CACHE_KEY);
}
