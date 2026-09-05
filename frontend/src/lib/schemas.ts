import { z } from "zod";

export const JOB_TYPES = ["Internship", "Full-time", "Contract"] as const;

export const profileSchema = z.object({
  name: z.string().min(1, "Give the profile a name").max(120),
  target_roles: z.array(z.string()).min(1, "Add at least one target role"),
  locations: z.array(z.string()).min(1, "Add at least one location"),
  job_types: z.array(z.string()).min(1, "Pick at least one job type"),
  must_have_skills: z.array(z.string()),
  nice_to_have_skills: z.array(z.string()),
  exclude_companies: z.array(z.string()),
  watchlist_companies: z.array(z.string()),
  min_match_percent: z.coerce.number().int().min(0).max(100),
  min_salary: z.coerce.number().int().min(0),
  schedule_cron: z.string().max(120).nullable(),
  timezone: z.string().min(1).max(64),
});

export type ProfileForm = z.infer<typeof profileSchema>;

export const emptyProfile: ProfileForm = {
  name: "",
  target_roles: [],
  locations: [],
  job_types: [],
  must_have_skills: [],
  nice_to_have_skills: [],
  exclude_companies: [],
  watchlist_companies: [],
  min_match_percent: 50,
  min_salary: 0,
  schedule_cron: null,
  timezone: "Asia/Kolkata",
};
