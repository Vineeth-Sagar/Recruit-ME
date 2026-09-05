"use client";

import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { resumesApi } from "@/lib/profiles";
import type { ResumeStatus } from "@/lib/types";
import { Button } from "@/components/ui/button";

type View = "idle" | "uploading" | ResumeStatus;

export function StepResume({
  resumeId,
  onResume,
}: {
  resumeId: string | null;
  onResume: (id: string | null) => void;
}) {
  const [view, setView] = useState<View>(resumeId ? "uploaded" : "idle");
  const [skills, setSkills] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!resumeId) return;
    let stopped = false;
    async function poll() {
      try {
        const r = await resumesApi.get(resumeId!);
        if (stopped) return;
        setView(r.status);
        if (r.status === "parsed") {
          setSkills(r.parse?.skills ?? []);
          return;
        }
        if (r.status === "failed") {
          setError(r.parse_error ?? "Parsing failed.");
          return;
        }
        setTimeout(poll, 1500);
      } catch {
        if (!stopped) setTimeout(poll, 2500);
      }
    }
    poll();
    return () => {
      stopped = true;
    };
  }, [resumeId]);

  async function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setSkills([]);
    setView("uploading");
    try {
      const r = await resumesApi.upload(file);
      onResume(r.id);
      setView(r.status);
    } catch (err) {
      setView("idle");
      const msg = err instanceof ApiError ? err.message : "Upload failed";
      setError(msg);
      toast.error(msg);
    }
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Upload a PDF résumé. We extract your skills to score jobs against it. You can skip this and
        add one later.
      </p>

      <input
        ref={fileRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={onPick}
      />
      <Button
        type="button"
        variant="outline"
        onClick={() => fileRef.current?.click()}
        disabled={view === "uploading" || view === "parsing"}
      >
        {view === "idle" || view === "failed" ? "Choose PDF" : "Replace PDF"}
      </Button>

      {view === "uploading" && <p className="text-sm text-muted-foreground">Uploading…</p>}
      {(view === "uploaded" || view === "parsing") && (
        <p className="text-sm text-muted-foreground">Parsing your résumé… this takes a few seconds.</p>
      )}
      {view === "failed" && (
        <p className="text-sm text-destructive">Couldn&apos;t parse that PDF: {error}</p>
      )}
      {view === "parsed" && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground">Extracted skills</p>
          <div className="flex flex-wrap gap-1.5">
            {skills.length ? (
              skills.map((s) => (
                <span
                  key={s}
                  className="rounded bg-secondary px-1.5 py-0.5 text-xs text-secondary-foreground"
                >
                  {s}
                </span>
              ))
            ) : (
              <span className="text-sm text-muted-foreground">No skills detected.</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
