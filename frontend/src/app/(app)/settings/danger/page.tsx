"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { accountApi } from "@/lib/settings";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

export default function DangerZonePage() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [confirmEmail, setConfirmEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const armed = !!user && confirmEmail.trim().toLowerCase() === user.email.toLowerCase() && !!password;

  async function onDelete(e: React.FormEvent) {
    e.preventDefault();
    if (!armed) return;
    setBusy(true);
    try {
      await accountApi.deleteAccount(password, confirmEmail.trim());
      toast.success("Your account and all its data have been deleted");
      await logout();
      router.replace("/login");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete the account");
      setBusy(false);
    }
  }

  return (
    <Card className="border-destructive/40">
      <CardHeader>
        <CardTitle className="text-base text-destructive">Delete account</CardTitle>
        <CardDescription>
          This permanently removes your profiles, résumés, runs, matches, stored site credentials,
          and every generated report. It cannot be undone.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onDelete} className="space-y-4">
          <Field label={`Type your email (${user?.email ?? ""}) to confirm`} htmlFor="confirm_email">
            <Input
              id="confirm_email"
              value={confirmEmail}
              onChange={(e) => setConfirmEmail(e.target.value)}
              autoComplete="off"
            />
          </Field>
          <Field label="Password" htmlFor="danger_pw">
            <Input
              id="danger_pw"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
          <Button type="submit" variant="default" className="bg-destructive hover:bg-destructive/90" disabled={!armed || busy}>
            {busy ? "Deleting…" : "Delete my account"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
