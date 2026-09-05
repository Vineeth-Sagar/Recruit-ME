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
