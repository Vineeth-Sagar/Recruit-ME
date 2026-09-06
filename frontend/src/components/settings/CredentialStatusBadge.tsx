import type { CredentialStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STYLES: Record<CredentialStatus, string> = {
  valid: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  invalid: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
  expired: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  unverified: "bg-muted text-muted-foreground",
};

export function CredentialStatusBadge({ status }: { status: CredentialStatus }) {
  return (
    <span
      className={cn(
        "rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide",
        STYLES[status],
      )}
    >
      {status}
    </span>
  );
}
