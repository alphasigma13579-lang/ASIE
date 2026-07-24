/**
 * Client session plumbing for the ASIE local platform.
 *
 * The backend is the source of truth for identity: Bearer sessions are stored
 * as SHA-256 token hashes server-side, and every organization-scoped request
 * carries X-ASIE-Organization-Id. This module only keeps the token in browser
 * sessionStorage (tab-scoped, cleared on tab close) and emits an event when
 * the server rejects it, so the app can return to the sign-in screen.
 */

const TOKEN_STORAGE_KEY = "asie.session_token.v1";
const ORGANIZATION_STORAGE_KEY = "asie.active_organization.v1";
const SESSION_EXPIRED_EVENT = "asie:session-expired";

function safeGet(key: string): string {
  try {
    return window.sessionStorage.getItem(key) ?? "";
  } catch {
    return "";
  }
}

function safeSet(key: string, value: string) {
  try {
    if (value) window.sessionStorage.setItem(key, value);
    else window.sessionStorage.removeItem(key);
  } catch {
    // Private browsing can deny storage; the session simply becomes memory-only.
  }
}

export function getSessionToken(): string {
  return safeGet(TOKEN_STORAGE_KEY);
}

export function setSessionToken(token: string) {
  safeSet(TOKEN_STORAGE_KEY, token);
}

export function getActiveOrganizationId(): string {
  return safeGet(ORGANIZATION_STORAGE_KEY);
}

export function setActiveOrganizationId(organizationId: string) {
  safeSet(ORGANIZATION_STORAGE_KEY, organizationId);
}

export function clearSession() {
  safeSet(TOKEN_STORAGE_KEY, "");
  safeSet(ORGANIZATION_STORAGE_KEY, "");
}

/** Called by the API layer when the server answers 401 for a held token. */
export function handleUnauthorized() {
  clearSession();
  try {
    window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
  } catch {
    // Non-DOM environments (tests) have no event target; nothing to notify.
  }
}

export function onSessionExpired(listener: () => void): () => void {
  const handler = () => listener();
  window.addEventListener(SESSION_EXPIRED_EVENT, handler);
  return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handler);
}
