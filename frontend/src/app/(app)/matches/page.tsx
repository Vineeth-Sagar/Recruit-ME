"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";

import { downloadMatchesXlsx, matchesApi } from "@/lib/runs";
import type { MatchOut, MatchStatus } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const STATUSES: (MatchStatus | "")[] = ["", "new", "saved", "applied", "dismissed"];

export default function MatchesPage() {
  return (
    <Suspense fallback={<Card className="mx-auto h-64 max-w-4xl animate-pulse" />}>
      <MatchesInner />
    </Suspense>
  );
}

function MatchesInner() {
  const qc = useQueryClient();
  const runFilter = useSearchParams().get("run") ?? undefined;
  const [minMatch, setMinMatch] = useState(0);
  const [status, setStatus] = useState<MatchStatus | "">("");
  const [q, setQ] = useState("");

  const query = { run: runFilter, min_match: minMatch, status: status || undefined, q: q || undefined, page_size: 100 };
  const { data, isLoading } = useQuery({
    queryKey: ["matches", query],
    queryFn: () => matchesApi.list(query),
  });

  const patch = useMutation({
    mutationFn: ({ id, s }: { id: string; s: MatchStatus }) => matchesApi.patch(id, s),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["matches"] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
    },
    onError: () => toast.error("Could not update the match"),
  });

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Matches</h1>
          <p className="text-sm text-muted-foreground">
            {data ? `${data.total} match${data.total === 1 ? "" : "es"}` : "…"}
            {runFilter ? " · filtered to one run" : ""}
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() =>
            downloadMatchesXlsx({ run: runFilter, min_match: minMatch, status: status || undefined, q: q || undefined }).catch(
              () => toast.error("Export failed"),
            )
          }
        >
          Export .xlsx
        </Button>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-xs text-muted-foreground">Min match {minMatch}%</span>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={minMatch}
            onChange={(e) => setMinMatch(Number(e.target.value))}
            className="w-40"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs text-muted-foreground">Status</span>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as MatchStatus | "")}
            className="h-9 rounded-md border border-input bg-transparent px-2 text-sm shadow-sm"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s || "any"}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs text-muted-foreground">Search</span>
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="company or title" className="w-52" />
        </label>
      </div>

      {isLoading && <Card className="h-40 animate-pulse" />}

      {!isLoading && data && data.items.length === 0 && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No matches for these filters.
          </CardContent>
        </Card>
      )}

      {data && data.items.length > 0 && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="p-3 font-medium">Company</th>
                  <th className="p-3 font-medium">Role</th>
                  <th className="p-3 font-medium">Match</th>
                  <th className="p-3 font-medium">Source</th>
                  <th className="p-3 font-medium">Status</th>
                  <th className="p-3" />
                </tr>
              </thead>
              <tbody>
                {data.items.map((m) => (
                  <MatchRow
                    key={m.id}
                    m={m}
                    onSet={(s) => patch.mutate({ id: m.id, s })}
                    busy={patch.isPending}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

function MatchRow({
  m,
  onSet,
  busy,
}: {
  m: MatchOut;
  onSet: (s: MatchStatus) => void;
  busy: boolean;
}) {
  return (
    <tr className="border-b align-top last:border-0">
      <td className="p-3 font-medium">
        {m.url ? (
          <a href={m.url} target="_blank" rel="noreferrer" className="hover:underline">
            {m.company}
          </a>
        ) : (
          m.company
        )}
      </td>
      <td className="p-3">
        <div>{m.title}</div>
        {m.location && <div className="text-xs text-muted-foreground">{m.location}</div>}
      </td>
      <td className="p-3 tabular-nums">{m.match_percentage}%</td>
      <td className="p-3 text-xs text-muted-foreground">{m.source}</td>
      <td className="p-3">
        <span className="rounded bg-secondary px-1.5 py-0.5 text-xs text-secondary-foreground">
          {m.status}
        </span>
      </td>
      <td className="p-3">
        <div className="flex justify-end gap-1">
          {(["saved", "applied", "dismissed"] as MatchStatus[]).map((s) => (
            <button
              key={s}
              type="button"
              disabled={busy || m.status === s}
              onClick={() => onSet(s)}
              className="rounded border border-input px-1.5 py-0.5 text-xs hover:bg-accent disabled:opacity-40"
            >
              {s}
            </button>
          ))}
        </div>
      </td>
    </tr>
  );
}
