const BASE = "/api/v1";

let accessToken: string | null = null;
let refreshInFlight: Promise<string | null> | null = null;

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

/** Ask the API for a fresh access token using the httpOnly refresh cookie. */
export async function refreshAccessToken(): Promise<string | null> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      const resp = await raw("/auth/refresh", { method: "POST" });
      if (!resp.ok) {
        accessToken = null;
        return null;
      }
      const data = (await resp.json()) as { access_token: string };
      accessToken = data.access_token;
      return accessToken;
    })().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

export async function apiFetch<T>(path: string, opts: FetchOpts = {}): Promise<T> {
  let resp = await raw(path, opts);

  if (resp.status === 401 && opts.auth) {
    const fresh = await refreshAccessToken();
    if (fresh) resp = await raw(path, opts);
  }

  if (resp.status === 204) return undefined as T;

  const text = await resp.text();
  const data = text ? JSON.parse(text) : null;

  if (!resp.ok) {
    const err = data?.error ?? {};
    throw new ApiError(resp.status, err.code ?? "error", err.message ?? resp.statusText);
  }
  return data as T;
}
