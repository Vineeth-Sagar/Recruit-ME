import { apiFetch, getAccessToken, refreshAccessToken } from "@/lib/api";
import type {
  DashboardSummary,
  MatchOut,
  MatchStatus,
  Page,
  RunDetail,
  RunOut,
} from "@/lib/types";

function qs(params?: object): string {
  if (!params) return "";
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "" && v !== null) p.set(k, String(v));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

export interface RunQuery {
  status?: string;
  profile?: string;
  page?: number;
  page_size?: number;
}

export interface MatchQuery {
  run?: string;
  profile?: string;
  status?: string;
  min_match?: number;
  q?: string;
  page?: number;
  page_size?: number;
}

export const runsApi = {
  create: (jobProfileId: string, idempotencyKey?: string) =>
    apiFetch<RunOut>("/runs", {
      method: "POST",
      json: { job_profile_id: jobProfileId },
      auth: true,
      headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
    }),
  list: (query?: RunQuery) => apiFetch<Page<RunOut>>(`/runs${qs(query)}`, { auth: true }),
  get: (id: string) => apiFetch<RunDetail>(`/runs/${id}`, { auth: true }),
  cancel: (id: string) => apiFetch<RunOut>(`/runs/${id}:cancel`, { method: "POST", auth: true }),
};

export const matchesApi = {
  list: (query?: MatchQuery) => apiFetch<Page<MatchOut>>(`/matches${qs(query)}`, { auth: true }),
  patch: (id: string, status: MatchStatus) =>
    apiFetch<MatchOut>(`/matches/${id}`, { method: "PATCH", json: { status }, auth: true }),
};

export const dashboardApi = {
  summary: () => apiFetch<DashboardSummary>("/dashboard/summary", { auth: true }),
};

/** Fetch the xlsx with auth and hand the browser a download. */
export async function downloadMatchesXlsx(query?: MatchQuery): Promise<void> {
  const url = `/api/v1/matches/export.xlsx${qs(query)}`;
  const send = async (token: string | null) =>
    fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      credentials: "include",
    });

  let resp = await send(getAccessToken());
  if (resp.status === 401) {
    const fresh = await refreshAccessToken();
    if (fresh) resp = await send(fresh);
  }
  if (!resp.ok) throw new Error("Export failed");

  const blob = await resp.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = "recruit-me-matches.xlsx";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(href);
}
