import type { RunStep } from "@/lib/types";

function mark(status: string): string {
  if (status === "succeeded") return "✓";
  if (status === "failed") return "✗";
  if (status === "skipped") return "⏭";
  if (status === "running") return "…";
  return "•";
}

export function RunTimeline({ steps }: { steps: RunStep[] }) {
  if (!steps.length) {
    return <p className="text-sm text-muted-foreground">Waiting for the run to start…</p>;
  }
  return (
    <ol className="space-y-1">
      {steps.map((s, i) => {
        const found = (s.detail as { found?: number })?.found;
        const err = (s.detail as { error?: string })?.error;
        return (
          <li key={`${s.name}-${i}`} className="flex items-baseline gap-2 text-sm">
            <span
              className={
                s.status === "failed"
                  ? "text-destructive"
                  : s.status === "succeeded"
                    ? "text-green-600 dark:text-green-400"
                    : "text-muted-foreground"
              }
              aria-hidden
            >
              {mark(s.status)}
            </span>
            <span className="font-mono text-xs">{s.name}</span>
            <span className="text-xs text-muted-foreground">{s.status}</span>
            {found != null && (
              <span className="text-xs text-muted-foreground">· {found} found</span>
            )}
            {err && <span className="truncate text-xs text-destructive">· {err}</span>}
          </li>
        );
      })}
    </ol>
  );
}
