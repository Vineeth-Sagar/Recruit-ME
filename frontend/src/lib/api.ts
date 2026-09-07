const BASE = "/api/v1";

let accessToken: string | null = null;
let refreshInFlight: Promise<string | null> | null = null;
let lastRefreshAt = 0;

export function setAccessToken(token: string | null) {
  accessToken = token;
}
export function getAccessToken() {
  return accessToken;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function safeJson(text: string): unknown {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null; // a proxy 502 / gateway page is not JSON — don't throw SyntaxError
  }
}

async function readBody<T>(resp: Response): Promise<T> {
  if (resp.status === 204) return undefined as T;
  const data = safeJson(await resp.text()) as { error?: { code?: string; message?: string } } | null;
  if (!resp.ok) {
    const err = data?.error ?? {};
    throw new ApiError(resp.status, err.code ?? "error", err.message ?? resp.statusText);
  }
  return data as T;
}

type FetchOpts = Omit<RequestInit, "body"> & {
  auth?: boolean;
  json?: unknown;
};

async function raw(path: string, opts: FetchOpts): Promise<Response> {
  const headers = new Headers(opts.headers);
  if (opts.json !== undefined) headers.set("Content-Type", "application/json");
  if (opts.auth && accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  return fetch(`${BASE}${path}`, {
    ...opts,
    headers,
    credentials: "include",
    body: opts.json !== undefined ? JSON.stringify(opts.json) : undefined,
  });
}

async function doRefresh(): Promise<string | null> {
  const resp = await raw("/auth/refresh", { method: "POST" });
  if (!resp.ok) {
    accessToken = null;
    // Drop a stale/invalid refresh cookie so the edge middleware stops
    // bouncing (app) routes back and forth with /login.
    await raw("/auth/logout", { method: "POST" }).catch(() => {});
    return null;
  }
  const data = (await resp.json()) as { access_token: string };
  accessToken = data.access_token;
  lastRefreshAt = Date.now();
  return accessToken;
}

/** Ask the API for a fresh access token using the httpOnly refresh cookie.
 *  The refresh token rotates on every call, so refreshes must be serialised:
 *  - across tabs, via the Web Locks API (a concurrent refresh in another tab
 *    would otherwise present a just-rotated token and trip reuse-detection);
 *  - within a tab, via `refreshInFlight`;
 *  - and for a few seconds after a success we reuse the token we just got
 *    rather than rotating again — unless `force` (the reused token still 401'd). */
export async function refreshAccessToken(force = false): Promise<string | null> {
  if (!force && accessToken && Date.now() - lastRefreshAt < 3000) return accessToken;
  if (refreshInFlight) return refreshInFlight;

  const locks = typeof navigator !== "undefined" ? navigator.locks : undefined;
  refreshInFlight = (async () => {
    if (locks) {
      return locks.request("recruit-refresh", async () => {
        if (!force && accessToken && Date.now() - lastRefreshAt < 3000) return accessToken;
        return doRefresh();
      });
    }
    return doRefresh();
  })().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

export async function apiFetch<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  let resp = await raw(path, opts);

  if (resp.status === 401 && opts.auth) {
    const stale = accessToken;
    let fresh = await refreshAccessToken();
    if (fresh && fresh === stale) fresh = await refreshAccessToken(true); // reused token was bad
    if (fresh) resp = await raw(path, opts);
  }

  return readBody<T>(resp);
}

/** multipart POST with the same access-token + refresh-on-401 handling. */
export async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  const send = () =>
    fetch(`${BASE}${path}`, {
      method: "POST",
      body: form,
      credentials: "include",
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
    });

  let resp = await send();
  if (resp.status === 401) {
    const fresh = await refreshAccessToken();
    if (fresh) resp = await send();
  }
  return readBody<T>(resp);
}
