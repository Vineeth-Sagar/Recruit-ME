"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { credentialsApi, SITE_LABELS, type CredentialInput } from "@/lib/settings";
import type { CredentialAuthType, CredentialSite, SiteCredential } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CredentialStatusBadge } from "@/components/settings/CredentialStatusBadge";

const AUTH_TYPES: CredentialAuthType[] = ["cookie", "api_key", "session"];

const PLACEHOLDER: Record<CredentialAuthType, string> = {
  cookie: "li_at=AQED...\njsessionid=ajax:123",
  api_key: "api_key=wf_live_xxx",
  session: "session=...",
};

/** Parse a "key=value" per line block into a flat string map. A line with no
 *  "=" becomes the api_key value when the auth type is api_key. */
function parseSecret(text: string, authType: CredentialAuthType): Record<string, string> {
  const out: Record<string, string> = {};
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) {
      if (authType === "api_key") out.api_key = trimmed;
      continue;
    }
    const key = trimmed.slice(0, eq).trim();
    const value = trimmed.slice(eq + 1).trim();
    if (key) out[key] = value;
  }
  return out;
}

export function CredentialCard({
  site,
  existing,
  disabled = false,
  disabledReason,
}: {
  site: CredentialSite;
  existing?: SiteCredential;
  disabled?: boolean;
  disabledReason?: string;
}) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [authType, setAuthType] = useState<CredentialAuthType>(existing?.auth_type ?? "cookie");
  const [label, setLabel] = useState(existing?.label ?? "");
  const [secretText, setSecretText] = useState("");

  const invalidate = () => qc.invalidateQueries({ queryKey: ["site-credentials"] });

  const save = useMutation({
    mutationFn: (body: CredentialInput) => credentialsApi.put(site, body),
    onSuccess: () => {
      toast.success(`${SITE_LABELS[site]} credential saved — verifying…`);
      setSecretText("");
      setOpen(false);
      invalidate();
      setTimeout(invalidate, 2500);
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not save the credential"),
  });

  const verify = useMutation({
    mutationFn: () => credentialsApi.verify(site),
    onSuccess: () => {
      toast.success("Re-check queued");
      setTimeout(invalidate, 2500);
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not queue a re-check"),
  });

  const remove = useMutation({
    mutationFn: () => credentialsApi.remove(site),
    onSuccess: () => {
      toast.success(`${SITE_LABELS[site]} credential removed`);
      invalidate();
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : "Could not remove the credential"),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const secret = parseSecret(secretText, authType);
    if (Object.keys(secret).length === 0) {
      toast.error("Add at least one key=value line");
      return;
    }
    save.mutate({ auth_type: authType, secret, label: label.trim() });
  }

  return (
    <Card className={disabled ? "opacity-60" : undefined}>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="text-base">
            {SITE_LABELS[site]}
            {existing ? (
              <span className="ml-2 align-middle">
                <CredentialStatusBadge status={existing.status} />
              </span>
            ) : null}
          </CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            {existing
              ? `${existing.auth_type}${existing.label ? ` · ${existing.label}` : ""} · ${
                  existing.last_verified_at
                    ? `checked ${new Date(existing.last_verified_at).toLocaleString()}`
                    : "not checked yet"
                }`
              : disabled
                ? (disabledReason ?? "Not available")
                : "No credential stored."}
          </p>
          {existing?.status === "invalid" && existing.verify_error ? (
            <p className="mt-1 text-xs text-destructive">{existing.verify_error}</p>
          ) : null}
        </div>
        <div className="flex shrink-0 gap-2">
          {existing ? (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={() => verify.mutate()}
                disabled={verify.isPending}
              >
                Re-check
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="text-destructive"
                onClick={() => remove.mutate()}
                disabled={remove.isPending}
              >
                Remove
              </Button>
            </>
          ) : null}
          <Button size="sm" variant={open ? "ghost" : "default"} onClick={() => setOpen(!open)}>
            {open ? "Cancel" : existing ? "Replace" : "Add"}
          </Button>
        </div>
      </CardHeader>

      {open && (
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor={`${site}-auth`}>Auth type</Label>
              <select
                id={`${site}-auth`}
                value={authType}
                onChange={(e) => setAuthType(e.target.value as CredentialAuthType)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                {AUTH_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor={`${site}-secret`}>Secret (one key=value per line)</Label>
              <textarea
                id={`${site}-secret`}
                value={secretText}
                onChange={(e) => setSecretText(e.target.value)}
                rows={3}
                placeholder={PLACEHOLDER[authType]}
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 font-mono text-xs shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
              <p className="text-xs text-muted-foreground">
                Sealed with authenticated encryption before it is stored. It is never shown again and
                only the background worker can open it.
              </p>
            </div>

            <Field label="Label (optional)" htmlFor={`${site}-label`}>
              <Input
                id={`${site}-label`}
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                maxLength={120}
                placeholder="e.g. personal account"
              />
            </Field>

            <Button type="submit" size="sm" disabled={save.isPending}>
              {save.isPending ? "Saving…" : "Save credential"}
            </Button>
          </form>
        </CardContent>
      )}
    </Card>
  );
}
