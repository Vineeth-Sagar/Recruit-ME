export type UserRole = "user" | "admin";
export type UserPlan = "free" | "pro";
export type UserStatus = "pending_verification" | "active" | "suspended";

export interface UserOut {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  plan: UserPlan;
  status: UserStatus;
  created_at: string;
}

export interface TokenOut {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface JobProfile {
  id: string;
  user_id: string;
  name: string;
  is_active: boolean;
  target_roles: string[];
  locations: string[];
  job_types: string[];
  must_have_skills: string[];
  nice_to_have_skills: string[];
  exclude_companies: string[];
  watchlist_companies: string[];
  min_match_percent: number;
  min_salary: number;
  big3_optin: boolean;
  schedule_cron: string | null;
  timezone: string;
  created_at: string;
  updated_at: string;
}

export type ResumeStatus = "uploaded" | "parsing" | "parsed" | "failed";

export interface ResumeParse {
  id: string;
  model: string;
  skills: string[];
  parsed_json: Record<string, unknown>;
  tokens_used: number;
  created_at: string;
}

export interface Resume {
  id: string;
  user_id: string;
  job_profile_id: string | null;
  original_filename: string;
  content_sha256: string;
  size_bytes: number;
  mime: string;
  status: ResumeStatus;
  parse_error: string | null;
  created_at: string;
  parse: ResumeParse | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export type RunTrigger = "manual" | "scheduled" | "api";
export type RunStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "partial"
  | "failed"
  | "cancelled";
export type MatchStatus = "new" | "saved" | "applied" | "dismissed";

export const TERMINAL_RUN_STATUSES: RunStatus[] = [
  "succeeded",
  "partial",
  "failed",
  "cancelled",
];

export interface RunStep {
  name: string;
  status: string;
  detail: Record<string, unknown>;
  at: string;
}

export interface RunSource {
  source: string;
  status: string;
  jobs_found: number;
  latency_ms: number;
  error: string | null;
}

export interface RunOut {
  id: string;
  job_profile_id: string;
  trigger: RunTrigger;
  status: RunStatus;
  attempt: number;
  queued_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  notified_at: string | null;
  error_summary: string | null;
  stats: Record<string, unknown>;
  created_at: string;
}

export interface RunDetail extends RunOut {
  steps: RunStep[];
  sources: RunSource[];
}

export interface MatchOut {
  id: string;
  run_id: string | null;
  job_profile_id: string | null;
  source: string;
  company: string;
  title: string;
  location: string;
  url: string;
  salary: string;
  posted_date: string;
  match_percentage: number;
  matched_skills: string[];
  missing_skills: string[];
  why_fit: string;
  urgency: string;
  recommended_action: string;
  status: MatchStatus;
  applied_at: string | null;
  created_at: string;
}

export interface DashboardSummary {
  runs_30d: number;
  last_run: { status: string; at: string } | null;
  matches_total: number;
  matches_new: number;
  applied_count: number;
  match_rate_series: { date: string; pct: number; count: number }[];
  top_missing_skills: { skill: string; n: number }[];
}
