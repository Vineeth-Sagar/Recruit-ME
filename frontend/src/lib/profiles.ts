import { apiFetch, apiUpload } from "@/lib/api";
import type { ProfileForm } from "@/lib/schemas";
import type { JobProfile, Resume } from "@/lib/types";

export const profilesApi = {
  list: () => apiFetch<JobProfile[]>("/job-profiles", { auth: true }),
  get: (id: string) => apiFetch<JobProfile>(`/job-profiles/${id}`, { auth: true }),
  create: (body: ProfileForm) =>
    apiFetch<JobProfile>("/job-profiles", { method: "POST", json: body, auth: true }),
  update: (id: string, body: Partial<ProfileForm>) =>
    apiFetch<JobProfile>(`/job-profiles/${id}`, { method: "PATCH", json: body, auth: true }),
  remove: (id: string) =>
    apiFetch<void>(`/job-profiles/${id}`, { method: "DELETE", auth: true }),
  activate: (id: string) =>
    apiFetch<JobProfile>(`/job-profiles/${id}:activate`, { method: "POST", auth: true }),
  deactivate: (id: string) =>
    apiFetch<JobProfile>(`/job-profiles/${id}:deactivate`, { method: "POST", auth: true }),
};

export const resumesApi = {
  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiUpload<Resume>("/resumes", fd);
  },
  get: (id: string) => apiFetch<Resume>(`/resumes/${id}`, { auth: true }),
  link: (id: string, jobProfileId: string | null) =>
    apiFetch<Resume>(`/resumes/${id}`, {
      method: "PATCH",
      json: { job_profile_id: jobProfileId },
      auth: true,
    }),
  remove: (id: string) => apiFetch<void>(`/resumes/${id}`, { method: "DELETE", auth: true }),
};
