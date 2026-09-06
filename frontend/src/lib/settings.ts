import { apiFetch } from "@/lib/api";
import type { CredentialAuthType, CredentialSite, SiteCredential } from "@/lib/types";

export interface CredentialInput {
  auth_type: CredentialAuthType;
  secret: Record<string, string>;
  label?: string;
}

export const BIG3_SITES: CredentialSite[] = ["linkedin", "indeed", "glassdoor"];

export const SITE_LABELS: Record<CredentialSite, string> = {
  linkedin: "LinkedIn",
  indeed: "Indeed",
  glassdoor: "Glassdoor",
  wellfound: "Wellfound",
};

export const credentialsApi = {
  list: () => apiFetch<SiteCredential[]>("/me/site-credentials", { auth: true }),
  put: (site: CredentialSite, body: CredentialInput) =>
    apiFetch<SiteCredential>(`/me/site-credentials/${site}`, {
      method: "PUT",
      json: body,
      auth: true,
    }),
  verify: (site: CredentialSite) =>
    apiFetch<SiteCredential>(`/me/site-credentials/${site}:verify`, {
      method: "POST",
      auth: true,
    }),
  remove: (site: CredentialSite) =>
    apiFetch<void>(`/me/site-credentials/${site}`, { method: "DELETE", auth: true }),
};

export const accountApi = {
  updateName: (full_name: string) =>
    apiFetch<{ full_name: string }>("/me", { method: "PATCH", json: { full_name }, auth: true }),
  changePassword: (current_password: string, new_password: string) =>
    apiFetch<void>("/me/password", {
      method: "POST",
      json: { current_password, new_password },
      auth: true,
    }),
  requestEmailChange: (new_email: string, current_password: string) =>
    apiFetch<{ status: string }>("/me/email", {
      method: "POST",
      json: { new_email, current_password },
      auth: true,
    }),
  confirmEmailChange: (token: string) =>
    apiFetch<void>("/auth/confirm-email-change", { method: "POST", json: { token } }),
  deleteAccount: (password: string, confirm_email: string) =>
    apiFetch<void>("/me", { method: "DELETE", json: { password, confirm_email }, auth: true }),
};
