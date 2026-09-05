"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { profilesApi, resumesApi } from "@/lib/profiles";
import { emptyProfile, profileSchema, type ProfileForm } from "@/lib/schemas";
import type { JobProfile } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StepFilters } from "./StepFilters";
import { StepLocations } from "./StepLocations";
import { StepResume } from "./StepResume";
import { StepReview } from "./StepReview";
import { StepRoles } from "./StepRoles";

const STEPS = ["Roles", "Where", "Filters", "Résumé", "Review"] as const;

const STEP_FIELDS: (keyof ProfileForm)[][] = [
  ["target_roles"],
  ["locations", "job_types", "min_salary"],
  ["must_have_skills", "nice_to_have_skills", "exclude_companies", "watchlist_companies", "min_match_percent"],
  [],
  ["name", "schedule_cron", "timezone"],
];

function toForm(p: JobProfile): ProfileForm {
  const { id, user_id, is_active, big3_optin, created_at, updated_at, ...rest } = p;
  void id;
  void user_id;
  void is_active;
  void big3_optin;
  void created_at;
  void updated_at;
  return rest;
}

export function ProfileWizard({ mode, profileId }: { mode: "create" | "edit"; profileId?: string }) {
  const router = useRouter();
  const draftKey = `rmwiz:${mode}:${profileId ?? "new"}`;
  const methods = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: emptyProfile,
    mode: "onTouched",
  });
  const [step, setStep] = useState(0);
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [ready, setReady] = useState(mode === "create");
  const restored = useRef(false);

  // ── restore ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (restored.current) return;
    restored.current = true;

    if (mode === "edit" && profileId) {
      profilesApi
        .get(profileId)
        .then((p) => methods.reset(toForm(p)))
        .catch(() => toast.error("Could not load that profile"))
        .finally(() => setReady(true));
      return;
    }
    try {
      const raw = localStorage.getItem(draftKey);
      if (raw) {
        const d = JSON.parse(raw);
        if (d.values) methods.reset({ ...emptyProfile, ...d.values });
        setResumeId(d.resumeId ?? null);
        setStep(typeof d.step === "number" ? d.step : 0);
      }
    } catch {
      /* ignore */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── autosave (create only) ─────────────────────────────────────────────
  const values = methods.watch();
  useEffect(() => {
    if (mode !== "create") return;
    const t = setTimeout(() => {
      try {
        localStorage.setItem(draftKey, JSON.stringify({ values, resumeId, step }));
      } catch {
        /* ignore */
      }
    }, 400);
    return () => clearTimeout(t);
  }, [values, resumeId, step, mode, draftKey]);

  async function next() {
    const fields = STEP_FIELDS[step];
    if (fields.length && !(await methods.trigger(fields))) return;
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  }

  async function onSubmit(v: ProfileForm) {
    try {
      const saved =
        mode === "edit" && profileId
          ? await profilesApi.update(profileId, v)
          : await profilesApi.create(v);
      if (resumeId) {
        await resumesApi.link(resumeId, saved.id).catch(() => null);
      }
      try {
        localStorage.removeItem(draftKey);
      } catch {
        /* ignore */
      }
      toast.success(mode === "edit" ? "Profile updated" : "Profile created");
      router.push("/profiles");
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Could not save the profile");
    }
  }

  if (!ready) {
    return <Card className="h-72 animate-pulse" />;
  }

  const isLast = step === STEPS.length - 1;

  return (
    <FormProvider {...methods}>
      <Card>
        <CardHeader>
          <div className="flex flex-wrap gap-1.5 text-xs">
            {STEPS.map((label, i) => (
              <span
                key={label}
                className={`rounded px-2 py-1 ${
                  i === step
                    ? "bg-primary text-primary-foreground"
                    : i < step
                      ? "bg-secondary text-secondary-foreground"
                      : "text-muted-foreground"
                }`}
              >
                {i + 1}. {label}
              </span>
            ))}
          </div>
          <CardTitle className="pt-2 text-lg">{STEPS[step]}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={methods.handleSubmit(onSubmit)}>
            {step === 0 && <StepRoles />}
            {step === 1 && <StepLocations />}
            {step === 2 && <StepFilters />}
            {step === 3 && <StepResume resumeId={resumeId} onResume={setResumeId} />}
            {step === 4 && <StepReview hasResume={!!resumeId} />}

            <div className="mt-6 flex justify-between">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setStep((s) => Math.max(s - 1, 0))}
                disabled={step === 0}
              >
                Back
              </Button>
              {isLast ? (
                <Button type="submit" disabled={methods.formState.isSubmitting}>
                  {mode === "edit" ? "Save changes" : "Create profile"}
                </Button>
              ) : (
                <Button type="button" onClick={next}>
                  Next
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>
    </FormProvider>
  );
}
