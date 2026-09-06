"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { profilesApi } from "@/lib/profiles";
import type { JobProfile } from "@/lib/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function Big3ConsentPanel() {
  const qc = useQueryClient();
  const { data: profiles, isLoading } = useQuery({
    queryKey: ["job-profiles"],
    queryFn: profilesApi.list,
  });

  const toggle = useMutation({
    mutationFn: (p: JobProfile) => profilesApi.setBig3Optin(p.id, !p.big3_optin),
    onSuccess: (updated) => {
      toast.success(
        updated.big3_optin
          ? `LinkedIn / Indeed / Glassdoor enabled for “${updated.name}”`
          : `Big-3 sources disabled for “${updated.name}”`,
      );
      qc.invalidateQueries({ queryKey: ["job-profiles"] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not update the profile"),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">LinkedIn, Indeed &amp; Glassdoor</CardTitle>
        <CardDescription>Off by default. Read this before you turn it on.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2 rounded-md border border-amber-300/60 bg-amber-50 p-3 text-xs leading-relaxed text-amber-900 dark:border-amber-800/60 dark:bg-amber-950/30 dark:text-amber-200">
          <p>
            These three sites are scraped through <code>python-jobspy</code>. Automated access is
            against each site&rsquo;s Terms of Service, their pages change without notice, and heavy
            use can get an account or IP rate-limited or blocked.
          </p>
          <p>
            Enable this only for accounts you own and are willing to put at risk, and keep request
            volume low. Recruit-ME never applies to a job for you — it only reads listings. You are
            responsible for how you use it.
          </p>
        </div>

        {isLoading && <div className="h-16 animate-pulse rounded-md bg-muted" />}

        {!isLoading && profiles && profiles.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No job profiles yet.{" "}
            <Link href="/profiles/new" className="text-foreground underline">
              Create one
            </Link>{" "}
            to choose where the big-3 run.
          </p>
        )}

        {profiles && profiles.length > 0 && (
          <ul className="divide-y rounded-md border">
            {profiles.map((p) => (
              <li key={p.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                <span className="truncate">{p.name}</span>
                <label className="flex shrink-0 cursor-pointer items-center gap-2 text-xs text-muted-foreground">
                  <span>{p.big3_optin ? "Enabled" : "Disabled"}</span>
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-primary"
                    checked={p.big3_optin}
                    disabled={toggle.isPending}
                    onChange={() => toggle.mutate(p)}
                  />
                </label>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
