"use client";

import { useQuery } from "@tanstack/react-query";

import { profilesApi } from "@/lib/profiles";
import { BIG3_SITES, credentialsApi } from "@/lib/settings";
import type { CredentialSite } from "@/lib/types";
import { Card } from "@/components/ui/card";
import { Big3ConsentPanel } from "@/components/settings/Big3ConsentPanel";
import { CredentialCard } from "@/components/settings/CredentialCard";

const ALL_SITES: CredentialSite[] = ["wellfound", "linkedin", "indeed", "glassdoor"];

export default function CredentialsSettingsPage() {
  const creds = useQuery({
    queryKey: ["site-credentials"],
    queryFn: credentialsApi.list,
    refetchInterval: (q) =>
      (q.state.data ?? []).some((c) => c.status === "unverified") ? 3000 : false,
  });
  const profiles = useQuery({ queryKey: ["job-profiles"], queryFn: profilesApi.list });

  const anyOptIn = (profiles.data ?? []).some((p) => p.big3_optin);
  const bySite = new Map((creds.data ?? []).map((c) => [c.site, c]));

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Some sources need a signed-in session to return useful results. Credentials are encrypted at
        rest and only the background worker can decrypt them; the API never returns the secret.
      </p>

      {creds.isLoading && <Card className="h-24 animate-pulse" />}

      {creds.data && (
        <div className="space-y-3">
          {ALL_SITES.map((site) => {
            const gated = BIG3_SITES.includes(site) && !anyOptIn;
            return (
              <CredentialCard
                key={site}
                site={site}
                existing={bySite.get(site)}
                disabled={gated}
                disabledReason="Enable this site for a job profile below before adding a credential."
              />
            );
          })}
        </div>
      )}

      <Big3ConsentPanel />
    </div>
  );
}
