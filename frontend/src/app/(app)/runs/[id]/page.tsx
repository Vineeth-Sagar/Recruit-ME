"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { runsApi } from "@/lib/runs";
import { TERMINAL_RUN_STATUSES, type RunStatus } from "@/lib/types";
import { useRunEvents } from "@/lib/sse";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RunTimeline } from "@/components/runs/RunTimeline";
import { StatusPill } from "@/components/runs/StatusPill";

export default function RunDetailPage({ params }: { params: { id: string } }) {
  const qc = useQueryClient();
  const { data: run } = useQuery({
    queryKey: ["run", params.id],
    queryFn: () => runsApi.get(params.id),
    refetchInterval: (q) =>
      q.state.data && !TERMINAL_RUN_STATUSES.includes(q.state.data.status) ? 2500 : false,
  });

  const live = run ? !TERMINAL_RUN_STATUSES.includes(run.status) : false;
  const { steps: liveSteps, status: liveStatus } = useRunEvents(params.id, live);

  const cancel = useMutation({
    mutationFn: () => runsApi.cancel(params.id),
    onSuccess: () => {
      toast.success("Run cancelled");
      qc.invalidateQueries({ queryKey: ["run", params.id] });
      qc.invalidateQueries({ queryKey: ["runs"] });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not cancel"),
  });

  if (!run) return <Card className="mx-auto h-72 max-w-2xl animate-pulse" />;

  const steps = liveSteps.length > run.steps.length ? liveSteps : run.steps;
  const status: RunStatus = liveStatus ?? run.status;
  const stats = run.stats as Record<string, unknown>;

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div className="flex items-center justify-between">
        <Link href="/runs" className="text-sm text-muted-foreground hover:text-foreground">
          ← Runs
        </Link>
        {live && (
          <Button variant="outline" size="sm" onClick={() => cancel.mutate()} disabled={cancel.isPending}>
            Cancel run
          </Button>
        )}
      </div>

      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold tracking-tight">Run</h1>
        <StatusPill status={status} />
        <span className="text-xs text-muted-foreground">
          {run.trigger} · attempt {run.attempt}
        </span>
      </div>

      {run.error_summary && (
        <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{run.error_summary}</p>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Steps</CardTitle>
        </CardHeader>
        <CardContent>
          <RunTimeline steps={steps} />
        </CardContent>
      </Card>

      {run.sources.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Sources</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <tbody>
                {run.sources.map((s) => (
                  <tr key={s.source} className="border-b last:border-0">
                    <td className="py-1.5 pr-3 font-mono text-xs">{s.source}</td>
                    <td className="py-1.5 pr-3 text-muted-foreground">{s.status}</td>
                    <td className="py-1.5 text-right tabular-nums">{s.jobs_found} jobs</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {TERMINAL_RUN_STATUSES.includes(status) && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Result</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {String(stats.scraped ?? 0)} scraped · {String(stats.new ?? 0)} new ·{" "}
            {String(stats.matched ?? 0)} matched
            {stats.ai_degraded ? " · AI degraded (keyword fallback)" : ""}
            {run.job_profile_id && (
              <>
                {" "}
                ·{" "}
                <Link href={`/matches?run=${run.id}`} className="text-foreground underline">
                  view matches
                </Link>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
