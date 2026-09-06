"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { profilesApi } from "@/lib/profiles";
import { runsApi } from "@/lib/runs";
import { Button } from "@/components/ui/button";

export function RunNowButton() {
  const router = useRouter();
  const qc = useQueryClient();
  const { data: profiles, isLoading } = useQuery({
    queryKey: ["job-profiles"],
    queryFn: profilesApi.list,
  });
  const [selected, setSelected] = useState("");

  const run = useMutation({
    mutationFn: (profileId: string) => runsApi.create(profileId),
    onSuccess: (r) => {
      toast.success("Run started");
      qc.invalidateQueries({ queryKey: ["runs"] });
      router.push(`/runs/${r.id}`);
    },
    onError: (e) =>
      toast.error(e instanceof ApiError ? e.message : "Could not start the run"),
  });

  if (isLoading) return <Button disabled>Run now</Button>;

  const list = profiles ?? [];
  if (list.length === 0) {
    return (
      <Button asChild variant="outline">
        <Link href="/profiles/new">Build a profile first</Link>
      </Button>
    );
  }

  const profileId = selected || list[0].id;
  return (
    <div className="flex items-center gap-2">
      {list.length > 1 && (
        <select
          aria-label="Profile to run"
          value={profileId}
          onChange={(e) => setSelected(e.target.value)}
          className="h-9 rounded-md border border-input bg-transparent px-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          {list.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      )}
      <Button onClick={() => run.mutate(profileId)} disabled={run.isPending}>
        {run.isPending ? "Starting…" : "Run now"}
      </Button>
    </div>
  );
}
