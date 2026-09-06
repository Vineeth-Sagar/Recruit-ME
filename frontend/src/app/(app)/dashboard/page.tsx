"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { useAuth } from "@/lib/auth";
import { dashboardApi, matchesApi } from "@/lib/runs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkline } from "@/components/charts/Sparkline";
import { RunNowButton } from "@/components/runs/RunNowButton";

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: summary } = useQuery({ queryKey: ["dashboard-summary"], queryFn: dashboardApi.summary });
  const { data: latest } = useQuery({
    queryKey: ["matches", { page_size: 5 }],
    queryFn: () => matchesApi.list({ page_size: 5 }),
  });

  const tiles = [
    { label: "Runs (30d)", value: summary?.runs_30d ?? "—" },
    { label: "Matches", value: summary?.matches_total ?? "—" },
    { label: "New", value: summary?.matches_new ?? "—" },
    { label: "Applied", value: summary?.applied_count ?? "—" },
  ];

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Signed in as {user?.email}</p>
        </div>
        <RunNowButton />
      </div>

      {user?.status === "pending_verification" && (
        <Card className="border-amber-300 bg-amber-50 dark:bg-amber-950/30">
          <CardHeader>
            <CardTitle className="text-base">Confirm your email</CardTitle>
            <CardDescription>We sent a confirmation link.</CardDescription>
          </CardHeader>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-4">
        {tiles.map((t) => (
          <Card key={t.label}>
            <CardHeader className="pb-2">
              <CardDescription>{t.label}</CardDescription>
              <CardTitle className="text-3xl tabular-nums">{t.value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Match rate — 14 days</CardTitle>
            <CardDescription>Average match % of jobs found each day</CardDescription>
          </CardHeader>
          <CardContent>
            {summary ? (
              <Sparkline
                points={summary.match_rate_series.map((d) => d.pct)}
                labels={summary.match_rate_series.map((d) => `${d.date}: ${d.pct}%`)}
                ariaLabel="14-day average match percentage"
              />
            ) : (
              <div className="h-11 animate-pulse rounded bg-muted" />
            )}
            {summary?.last_run && (
              <p className="mt-2 text-xs text-muted-foreground">
                Last run {summary.last_run.status} ·{" "}
                {new Date(summary.last_run.at).toLocaleString()}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Top missing skills</CardTitle>
            <CardDescription>Across matches in the last 30 days</CardDescription>
          </CardHeader>
          <CardContent>
            {summary && summary.top_missing_skills.length ? (
              <ul className="space-y-1 text-sm">
                {summary.top_missing_skills.map((s) => (
                  <li key={s.skill} className="flex justify-between">
                    <span>{s.skill}</span>
                    <span className="tabular-nums text-muted-foreground">{s.n}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">No data yet — run a job hunt.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">Latest matches</CardTitle>
          <Link href="/matches" className="text-sm text-muted-foreground hover:text-foreground">
            View all
          </Link>
        </CardHeader>
        <CardContent>
          {latest && latest.items.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <tbody>
                  {latest.items.map((m) => (
                    <tr key={m.id} className="border-b last:border-0">
                      <td className="py-1.5 pr-3 font-medium">{m.company}</td>
                      <td className="py-1.5 pr-3 text-muted-foreground">{m.title}</td>
                      <td className="py-1.5 text-right tabular-nums">{m.match_percentage}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No matches yet — hit <span className="font-medium text-foreground">Run now</span> above.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
