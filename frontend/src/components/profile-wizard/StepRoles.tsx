"use client";

import { Controller, useFormContext } from "react-hook-form";

import type { ProfileForm } from "@/lib/schemas";
import { Field } from "@/components/ui/field";
import { TagInput } from "@/components/ui/tag-input";

export function StepRoles() {
  const { control, formState } = useFormContext<ProfileForm>();
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Which roles should the automation search for? Use the exact titles you&apos;d search
        yourself.
      </p>
      <Field
        label="Target roles"
        htmlFor="target_roles"
        error={formState.errors.target_roles?.message}
      >
        <Controller
          control={control}
          name="target_roles"
          render={({ field }) => (
            <TagInput
              id="target_roles"
              value={field.value}
              onChange={field.onChange}
              placeholder="Backend Engineer, SDE Intern…  (Enter to add)"
            />
          )}
        />
      </Field>
    </div>
  );
}
