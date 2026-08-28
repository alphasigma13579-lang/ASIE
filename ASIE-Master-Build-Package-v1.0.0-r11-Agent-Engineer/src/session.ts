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
let sessionRevision = 0;
const contextListeners = new Set<() => void>();

/** Monotonic lifetime: A -> B -> A must not revive an old response. */
export function getSessionRevision(): number {
  return sessionRevision;
}

/** Subscribe the workspace boundary; no token or tenant value enters the key. */
export function onSessionContextChanged(listener: () => void): () => void {
  contextListeners.add(listener);
  return () => { contextListeners.delete(listener); };
}

/** Reject stale replies before publishing data or expiring another session. */
export function assertSessionRevision(revision: number): void {
  if (revision !== sessionRevision) {
    throw new Error("تغير الحساب أو المؤسسة؛ أعد المحاولة في المساحة الحالية.");
  }
}

/** Publish only effective, atomic changes to the existing tab-scoped storage. */
function updateSessionContext(token: string, organizationId: string): void {
  const previousToken = getSessionToken();
  const previousOrganization = getActiveOrganizationId();
  const tokenWritten = safeSet(TOKEN_STORAGE_KEY, token);
  const organizationWritten = safeSet(ORGANIZATION_STORAGE_KEY, organizationId);

  // sessionStorage has no transaction. Never publish a token/organization pair
  // unless both writes are observable; compensate before this tab sees a change.
  if (
    !tokenWritten ||
    !organizationWritten ||
    getSessionToken() !== token ||
    getActiveOrganizationId() !== organizationId
  ) {
    safeSet(TOKEN_STORAGE_KEY, previousToken);
    safeSet(ORGANIZATION_STORAGE_KEY, previousOrganization);
    return;
  }

  if (previousToken !== token || previousOrganization !== organizationId) {
    sessionRevision += 1;
    contextListeners.forEach((listener) => listener());
  }
}

function safeGet(key: string): string {
  try {
    return window.sessionStorage.getItem(key) ?? "";
  } catch {
    return "";
  }
}

function safeSet(key: string, value: string): boolean {
  try {
    if (value) window.sessionStorage.setItem(key, value);
    else window.sessionStorage.removeItem(key);
    return true;
  } catch {
    // Storage can be denied; unavailable credentials must fail closed.
    return false;
  }
}

export function getSessionToken(): string {
  return safeGet(TOKEN_STORAGE_KEY);
}

export function setSessionToken(token: string) {
  // A new identity must not inherit the former identity's organization.
  updateSessionContext(token, token === getSessionToken() ? getActiveOrganizationId() : "");
}

export function getActiveOrganizationId(): string {
  return safeGet(ORGANIZATION_STORAGE_KEY);
}

export function setActiveOrganizationId(organizationId: string) {
  updateSessionContext(getSessionToken(), organizationId);
}

export function clearSession() {
  updateSessionContext("", "");
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
