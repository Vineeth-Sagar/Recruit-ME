"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { runsApi } from "@/lib/runs";
import { TERMINAL_RUN_STATUSES } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { RunNowButton } from "@/components/runs/RunNowButton";
import { StatusPill } from "@/components/runs/StatusPill";

function duration(a: string | null, b: string | null): string {
  if (!a || !b) return "—";
  const s = Math.max(0, (new Date(b).getTime() - new Date(a).getTime()) / 1000);
  return s < 60 ? `${s.toFixed(0)}s` : `${(s / 60).toFixed(1)}m`;
}

export default function RunsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["runs"],
    queryFn: () => runsApi.list({ page_size: 50 }),
    refetchInterval: (q) => {
      const items = q.state.data?.items ?? [];
      return items.some((r) => !TERMINAL_RUN_STATUSES.includes(r.status)) ? 2000 : false;
    },
  });

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
          <p className="text-sm text-muted-foreground">Every job-hunt execution and its result.</p>
        </div>
        <RunNowButton />
      </div>

      {isLoading && <Card className="h-24 animate-pulse" />}

      {!isLoading && data && data.items.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No runs yet. Hit <span className="font-medium text-foreground">Run now</span>.
          </CardContent>
        </Card>
      )}

      {data && data.items.length > 0 && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="p-3 font-medium">Status</th>
                  <th className="p-3 font-medium">Trigger</th>
                  <th className="p-3 font-medium">Matches</th>
                  <th className="p-3 font-medium">Duration</th>
                  <th className="p-3 font-medium">Started</th>
                  <th className="p-3" />
                </tr>
              </thead>
              <tbody>
                {data.items.map((r) => (
                  <tr key={r.id} className="border-b last:border-0 hover:bg-muted/40">
                    <td className="p-3">
                      <StatusPill status={r.status} />
                    </td>
                    <td className="p-3 text-muted-foreground">{r.trigger}</td>
                    <td className="p-3 tabular-nums">{String(r.stats?.matched ?? "—")}</td>
                    <td className="p-3 tabular-nums">{duration(r.started_at, r.finished_at)}</td>
                    <td className="p-3 text-muted-foreground">
                      {r.started_at ? new Date(r.started_at).toLocaleString() : "—"}
                    </td>
                    <td className="p-3 text-right">
                      <Link
                        href={`/runs/${r.id}`}
                        className="text-muted-foreground hover:text-foreground"
                      >
                        Open
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
