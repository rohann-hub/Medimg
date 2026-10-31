// API client with OAuth2/JWT handling.
//
// * access token (JWT, ~15 min) goes in `Authorization: Bearer …` on every call
// * on a 401 the client silently calls /auth/refresh once (refresh tokens rotate), then retries
// * concurrent 401s share ONE refresh request, so rotation doesn't revoke itself
// * images are fetched with the header and turned into blob URLs — scans never sit behind
//   unauthenticated <img src> links
//
// Tokens live in sessionStorage (cleared when the tab closes). A hardened deployment would keep the
// refresh token in an HttpOnly, Secure, SameSite=Strict cookie instead, out of JavaScript's reach.
const KEY = "medimg.auth";

function load() {
  try { return JSON.parse(sessionStorage.getItem(KEY)) || {}; } catch { return {}; }
}
function save(v) {
  try { v ? sessionStorage.setItem(KEY, JSON.stringify(v)) : sessionStorage.removeItem(KEY); } catch {}
}

export const auth = {
  get access() { return load().access_token || null; },
  get refresh() { return load().refresh_token || null; },
  get user() { return load().user || null; },
  set(tokens) { save(tokens ? { access_token: tokens.access_token, refresh_token: tokens.refresh_token, user: tokens.user } : null); },
};

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : detail?.message || JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

let refreshing = null;
async function refreshTokens() {
  if (!auth.refresh) return false;
  refreshing ??= (async () => {
    try {
      const res = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: auth.refresh }),
      });
      if (!res.ok) return false;
      auth.set(await res.json());
      return true;
    } catch {
      return false;
    } finally {
      setTimeout(() => { refreshing = null; }, 0);
    }
  })();
  return refreshing;
}

function signedOut() {
  auth.set(null);
  window.dispatchEvent(new Event("medimg:logout"));
}

// fetch with the bearer token; on 401 refresh once and retry
async function authedFetch(path, init = {}, retry = true) {
  const headers = { ...(init.headers || {}) };
  if (auth.access) headers.Authorization = `Bearer ${auth.access}`;
  const res = await fetch(`/api${path}`, { ...init, headers });
  if (res.status === 401 && retry && !path.startsWith("/auth/")) {
    if (await refreshTokens()) return authedFetch(path, init, false);
    signedOut();
  }
  return res;
}

async function req(path, { method = "GET", body, form } = {}) {
  const headers = body ? { "Content-Type": "application/json" } : {};
  const res = await authedFetch(path, { method, headers, body: form || (body && JSON.stringify(body)) });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.status === 204 ? null : res.json();
}

const blobCache = new Map();
export async function imageUrl(path) {
  if (blobCache.has(path)) return blobCache.get(path);
  const res = await authedFetch(path);
  if (res.status === 204 || res.status === 404) { blobCache.set(path, null); return null; }
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  const url = URL.createObjectURL(await res.blob());
  blobCache.set(path, url);
  return url;
}
export function clearImageCache(prefix = "") {
  for (const [k, v] of blobCache) if (k.startsWith(prefix)) { if (v) URL.revokeObjectURL(v); blobCache.delete(k); }
}

export const api = {
  async login(username, password) {
    const tokens = await req("/auth/login", { method: "POST", body: { username, password } });
    auth.set(tokens);
    return tokens.user;
  },
  async logout() {
    const rt = auth.refresh;
    auth.set(null);
    clearImageCache();
    if (rt) await fetch("/api/auth/logout", { method: "POST", headers: { "Content-Type": "application/json" },
                                               body: JSON.stringify({ refresh_token: rt }) }).catch(() => {});
  },
  me: () => req("/me"),
  changePassword: (current_password, new_password) =>
    req("/me/password", { method: "POST", body: { current_password, new_password } }),
  info: () => req("/info"),
  studies: () => req("/studies"),
  study: (id) => req(`/studies/${id}`),
  upload: (files) => {
    const fd = new FormData();
    for (const f of files) fd.append("files", f);
    return req("/upload", { method: "POST", form: fd });
  },
  decide: (predId, decision, comment) =>
    req(`/predictions/${predId}/decision`, { method: "POST", body: { decision, comment } }),
  reprocess: (id) => req(`/studies/${id}/reprocess`, { method: "POST" }),
  audit: (params = {}) => req(`/audit?${new URLSearchParams(params)}`),
  verifyAudit: () => req("/audit/verify"),
  users: () => req("/users"),
  createUser: (u) => req("/users", { method: "POST", body: u }),
  updateUser: (id, patch) => req(`/users/${id}`, { method: "PATCH", body: patch }),
};
