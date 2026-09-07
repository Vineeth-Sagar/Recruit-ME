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
 *  can't set headers). Returns the accumulated steps and the terminal status.
 *  Reconnects (bounded) when the server closes the stream on its poll cap or the
 *  connection drops before the run is terminal. */
export function useRunEvents(runId: string, enabled: boolean) {
  const [steps, setSteps] = useState<RunStep[]>([]);
  const [status, setStatus] = useState<RunStatus | null>(null);

  useEffect(() => {
    if (!enabled) return;
    const ctrl = new AbortController();
    let stopped = false;
    let attempts = 0;
    setSteps([]);
    setStatus(null);

    const open = (token: string | null) =>
      fetch(`/api/v1/runs/${runId}/events`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        credentials: "include",
        signal: ctrl.signal,
      });

    /** One connection. Returns true when the run reached a terminal state. */
    async function streamOnce(): Promise<boolean> {
      let resp = await open(getAccessToken());
      if (resp.status === 401) {
        const fresh = await refreshAccessToken();
        if (!fresh) return true; // can't auth — stop
        resp = await open(fresh);
      }
      if (!resp.ok || !resp.body) return false;

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (!stopped) {
        const { done, value } = await reader.read();
        if (done) return false; // server closed — caller decides whether to retry
        buffer += decoder.decode(value, { stream: true });
        let sep: number;
        while ((sep = buffer.indexOf("\n\n")) >= 0) {
          const raw = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          const ev = parseChunk(raw);
          if (!ev) continue;
          if (ev.event === "step") {
            const step = ev.data as unknown as RunStep;
            // A reconnect replays every step from the start — dedupe by name+at.
            setSteps((prev) =>
              prev.some((s) => s.name === step.name && s.at === step.at)
                ? prev
                : [...prev, step],
            );
          } else if (ev.event === "done") {
            const s = ev.data.status as string;
            if (s !== "gone") setStatus(s as RunStatus);
            return true;
          }
        }
      }
      return true; // stopped by cleanup
    }

    (async () => {
      while (!stopped && attempts < 20) {
        attempts += 1;
        let terminal = false;
        try {
          terminal = await streamOnce();
        } catch {
          terminal = false;
        }
        if (terminal || stopped) return;
        await new Promise((r) => setTimeout(r, 1500)); // brief backoff, then reconnect
      }
    })();

    return () => {
      stopped = true;
      ctrl.abort();
    };
  }, [runId, enabled]);

  return { steps, status };
}
