import type { RunStatus } from "@/lib/types";

const MAP: Record<RunStatus, { label: string; cls: string }> = {
  queued: { label: "Queued", cls: "bg-secondary text-secondary-foreground" },
  running: {
    label: "Running",
    cls: "bg-blue-100 text-blue-800 dark:bg-blue-950/50 dark:text-blue-300",
  },
  succeeded: {
    label: "Succeeded",
    cls: "bg-green-100 text-green-800 dark:bg-green-950/50 dark:text-green-300",
  },
  partial: {
    label: "Partial",
    cls: "bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300",
  },
  failed: {
    label: "Failed",
    cls: "bg-red-100 text-red-800 dark:bg-red-950/50 dark:text-red-300",
  },
  cancelled: { label: "Cancelled", cls: "bg-secondary text-muted-foreground" },
};

export function StatusPill({ status }: { status: RunStatus }) {
  const s = MAP[status] ?? { label: status, cls: "bg-secondary text-secondary-foreground" };
  return (
    <span className={`inline-flex rounded px-1.5 py-0.5 text-xs font-medium ${s.cls}`}>
      {s.label}
    </span>
  );
}
