"use client";

import { useFormContext } from "react-hook-form";

import type { ProfileForm } from "@/lib/schemas";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b py-1.5 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right">{value || "—"}</span>
    </div>
  );
}

export function StepReview({ hasResume }: { hasResume: boolean }) {
  const { register, watch, formState } = useFormContext<ProfileForm>();
  const v = watch();

  return (
    <div className="space-y-4">
      <Field label="Profile name" htmlFor="name" error={formState.errors.name?.message}>
        <Input id="name" placeholder="e.g. Backend Intern — Bengaluru" {...register("name")} />
      </Field>

      <Field
        label="Schedule (cron, optional — blank = manual only)"
        htmlFor="schedule_cron"
        error={formState.errors.schedule_cron?.message}
      >
        <Input
          id="schedule_cron"
          placeholder="0 2 * * *"
          {...register("schedule_cron", {
            setValueAs: (x) => (x === "" || x == null ? null : String(x)),
          })}
        />
      </Field>

      <Field label="Timezone" htmlFor="timezone" error={formState.errors.timezone?.message}>
        <Input id="timezone" {...register("timezone")} />
      </Field>

      <div className="rounded-md border p-3">
        <Row label="Target roles" value={v.target_roles.join(", ")} />
        <Row label="Locations" value={v.locations.join(", ")} />
        <Row label="Job types" value={v.job_types.join(", ")} />
        <Row label="Must-have" value={v.must_have_skills.join(", ")} />
        <Row label="Nice-to-have" value={v.nice_to_have_skills.join(", ")} />
        <Row label="Exclude" value={v.exclude_companies.join(", ")} />
        <Row label="Watchlist" value={v.watchlist_companies.join(", ")} />
        <Row label="Min match %" value={String(v.min_match_percent)} />
        <Row label="Min salary" value={String(v.min_salary)} />
        <Row label="Résumé" value={hasResume ? "attached" : "none yet"} />
      </div>
    </div>
  );
}
