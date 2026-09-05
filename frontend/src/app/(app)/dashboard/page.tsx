"use client";

import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Signed in as {user?.email}</p>
      </div>

      {user?.status === "pending_verification" && (
        <Card className="border-amber-300 bg-amber-50 dark:bg-amber-950/30">
          <CardHeader>
            <CardTitle className="text-base">Confirm your email</CardTitle>
            <CardDescription>
              We sent a confirmation link. You can keep setting things up in the meantime.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: "Job profiles", value: "—" },
          { label: "Runs (30d)", value: "—" },
          { label: "Applications sent", value: "—" },
        ].map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="pb-2">
              <CardDescription>{stat.label}</CardDescription>
              <CardTitle className="text-3xl">{stat.value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Next: build a job profile</CardTitle>
          <CardDescription>
            The profile builder, runs, and matches land in the following phases. Auth and accounts
            are done.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Account: {user?.role} · {user?.plan} · {user?.status}
        </CardContent>
      </Card>
    </div>
  );
}
