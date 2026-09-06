"use client";

import { useEffect, useState } from "react";

import { getAccessToken, refreshAccessToken } from "@/lib/api";
import type { RunStatus, RunStep } from "@/lib/types";

interface SseEvent {
  event: string;
  data: Record<string, unknown>;
}

function parseChunk(chunk: string): SseEvent | null {
  let event = "message";
  let data = "";
  for (const line of chunk.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data) return null;
  try {
    return { event, data: JSON.parse(data) };
  } catch {
    return null;
  }
}

/** Streams /api/v1/runs/{id}/events with the in-memory bearer token (EventSource
 *  can't set headers). Returns the accumulated steps and the terminal status. */
export function useRunEvents(runId: string, enabled: boolean) {
  const [steps, setSteps] = useState<RunStep[]>([]);
  const [status, setStatus] = useState<RunStatus | null>(null);

  useEffect(() => {
    if (!enabled) return;
    const ctrl = new AbortController();
    let stopped = false;
    setSteps([]);
    setStatus(null);

    async function stream() {
      const open = (token: string | null) =>
        fetch(`/api/v1/runs/${runId}/events`, {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          credentials: "include",
          signal: ctrl.signal,
        });

      let resp = await open(getAccessToken());
      if (resp.status === 401) {
        const fresh = await refreshAccessToken();
        if (!fresh) return;
        resp = await open(fresh);
      }
      if (!resp.ok || !resp.body) return;

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (!stopped) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let sep: number;
        while ((sep = buffer.indexOf("\n\n")) >= 0) {
          const raw = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          const ev = parseChunk(raw);
          if (!ev) continue;
          if (ev.event === "step") {
            setSteps((prev) => [...prev, ev.data as unknown as RunStep]);
          } else if (ev.event === "done") {
            setStatus(ev.data.status as RunStatus);
            return;
          }
        }
      }
    }

    stream().catch(() => {});
    return () => {
      stopped = true;
      ctrl.abort();
    };
  }, [runId, enabled]);

  return { steps, status };
}
