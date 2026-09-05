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
