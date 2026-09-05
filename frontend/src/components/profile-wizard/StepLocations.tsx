"use client";

import { Controller, useFormContext } from "react-hook-form";

import { JOB_TYPES, type ProfileForm } from "@/lib/schemas";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { TagInput } from "@/components/ui/tag-input";

export function StepLocations() {
  const { control, register, formState } = useFormContext<ProfileForm>();
  return (
    <div className="space-y-4">
      <Field label="Locations" htmlFor="locations" error={formState.errors.locations?.message}>
        <Controller
          control={control}
          name="locations"
          render={({ field }) => (
            <TagInput
              id="locations"
              value={field.value}
              onChange={field.onChange}
              placeholder="Bengaluru, Remote…  (Enter to add)"
            />
          )}
        />
      </Field>

      <Field label="Job types" htmlFor="job_types" error={formState.errors.job_types?.message}>
        <Controller
          control={control}
          name="job_types"
          render={({ field }) => (
            <div className="flex flex-wrap gap-2">
              {JOB_TYPES.map((jt) => {
                const on = field.value.includes(jt);
                return (
                  <button
                    key={jt}
                    type="button"
                    onClick={() =>
                      field.onChange(on ? field.value.filter((v) => v !== jt) : [...field.value, jt])
                    }
                    className={`rounded-md border px-3 py-1.5 text-sm ${
                      on
                        ? "border-primary bg-primary text-primary-foreground"
                        : "border-input hover:bg-accent"
                    }`}
                  >
                    {jt}
                  </button>
                );
              })}
            </div>
          )}
        />
      </Field>

      <Field
        label="Minimum salary (₹ LPA, 0 = any)"
        htmlFor="min_salary"
        error={formState.errors.min_salary?.message}
      >
        <Input id="min_salary" type="number" min={0} {...register("min_salary")} />
      </Field>
    </div>
  );
}
