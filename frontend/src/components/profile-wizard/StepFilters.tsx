"use client";

import { Controller, useFormContext } from "react-hook-form";

import type { ProfileForm } from "@/lib/schemas";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { TagInput } from "@/components/ui/tag-input";

const TAG_FIELDS: { name: keyof ProfileForm; label: string; placeholder: string }[] = [
  { name: "must_have_skills", label: "Must-have skills", placeholder: "Python, SQL…" },
  { name: "nice_to_have_skills", label: "Nice-to-have skills", placeholder: "Docker, Kubernetes…" },
  { name: "exclude_companies", label: "Exclude companies", placeholder: "Companies to skip" },
  { name: "watchlist_companies", label: "Watchlist companies", placeholder: "Always show these" },
];

export function StepFilters() {
  const { control, register, formState } = useFormContext<ProfileForm>();
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">All optional. Tune later from the dashboard.</p>
      {TAG_FIELDS.map((f) => (
        <Field key={f.name} label={f.label} htmlFor={f.name}>
          <Controller
            control={control}
            name={f.name}
            render={({ field }) => (
              <TagInput
                id={f.name}
                value={(field.value as string[]) ?? []}
                onChange={field.onChange}
                placeholder={f.placeholder}
              />
            )}
          />
        </Field>
      ))}
      <Field
        label="Minimum match % to include"
        htmlFor="min_match_percent"
        error={formState.errors.min_match_percent?.message}
      >
        <Input
          id="min_match_percent"
          type="number"
          min={0}
          max={100}
          {...register("min_match_percent")}
        />
      </Field>
    </div>
  );
}
