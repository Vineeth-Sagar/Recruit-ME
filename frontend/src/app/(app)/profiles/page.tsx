"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { toast } from "sonner";

import { profilesApi } from "@/lib/profiles";
import type { JobProfile } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ProfilesPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["job-profiles"],
    queryFn: profilesApi.list,
  });

  const toggle = useMutation({
    mutationFn: (p: JobProfile) =>
      p.is_active ? profilesApi.deactivate(p.id) : profilesApi.activate(p.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["job-profiles"] }),
    onError: () => toast.error("Could not update the profile"),
  });

  const remove = useMutation({
    mutationFn: (id: string) => profilesApi.remove(id),
    onSuccess: () => {
      toast.success("Profile deleted");
      qc.invalidateQueries({ queryKey: ["job-profiles"] });
    },
    onError: () => toast.error("Could not delete the profile"),
  });

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Job profiles</h1>
          <p className="text-sm text-muted-foreground">
            Each profile is a separate search — roles, filters, résumé, schedule.
          </p>
        </div>
        <Button asChild>
          <Link href="/profiles/new">New profile</Link>
        </Button>
      </div>

      {isLoading && <Card className="h-24 animate-pulse" />}

      {!isLoading && data && data.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No profiles yet.{" "}
            <Link href="/profiles/new" className="text-foreground underline">
              Build your first one
            </Link>
            .
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {data?.map((p) => (
          <Card key={p.id}>
            <CardHeader className="flex-row items-start justify-between space-y-0">
              <div>
                <CardTitle className="text-base">
                  {p.name}
                  {p.is_active ? (
                    <span className="ml-2 rounded bg-green-100 px-1.5 py-0.5 text-[10px] font-medium uppercase text-green-800 dark:bg-green-900/40 dark:text-green-300">
                      active
                    </span>
                  ) : null}
                </CardTitle>
                <p className="mt-1 text-xs text-muted-foreground">
                  {p.target_roles.slice(0, 3).join(", ") || "no roles"} ·{" "}
                  {p.locations.join(", ") || "no locations"}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button size="sm" variant="outline" onClick={() => toggle.mutate(p)}>
                  {p.is_active ? "Pause" : "Activate"}
                </Button>
                <Button size="sm" variant="ghost" asChild>
                  <Link href={`/profiles/${p.id}`}>Edit</Link>
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-destructive"
                  onClick={() => remove.mutate(p.id)}
                >
                  Delete
                </Button>
              </div>
            </CardHeader>
          </Card>
        ))}
      </div>
    </div>
  );
}
