"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { accountApi } from "@/lib/settings";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

export default function AccountSettingsPage() {
  const { user, refreshUser, logout } = useAuth();
  const router = useRouter();

  const [name, setName] = useState(user?.full_name ?? "");
  const [savingName, setSavingName] = useState(false);

  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [savingPw, setSavingPw] = useState(false);

  const [em, setEm] = useState({ email: "", password: "" });
  const [savingEm, setSavingEm] = useState(false);

  async function saveName(e: React.FormEvent) {
    e.preventDefault();
    setSavingName(true);
    try {
      await accountApi.updateName(name.trim());
      await refreshUser();
      toast.success("Name updated");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not update your name");
    } finally {
      setSavingName(false);
    }
  }

  async function savePassword(e: React.FormEvent) {
    e.preventDefault();
    if (pw.next !== pw.confirm) {
      toast.error("The new passwords don't match");
      return;
    }
    if (pw.next.length < 8) {
      toast.error("Use at least 8 characters");
      return;
    }
    setSavingPw(true);
    try {
      await accountApi.changePassword(pw.current, pw.next);
      toast.success("Password changed. Please sign in again.");
      await logout();
      router.replace("/login");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not change your password");
      setSavingPw(false);
    }
  }

  async function requestEmail(e: React.FormEvent) {
    e.preventDefault();
    setSavingEm(true);
    try {
      await accountApi.requestEmailChange(em.email.trim(), em.password);
      toast.success(`Confirm the change from the link we sent to ${em.email.trim()}`);
      setEm({ email: "", password: "" });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not start the email change");
    } finally {
      setSavingEm(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profile</CardTitle>
          <CardDescription>Signed in as {user?.email}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={saveName} className="space-y-4">
            <Field label="Full name" htmlFor="full_name">
              <Input
                id="full_name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={200}
              />
            </Field>
            <Button type="submit" size="sm" disabled={savingName}>
              {savingName ? "Saving…" : "Save"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Change password</CardTitle>
          <CardDescription>
            Changing your password signs out every other session, including this one.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={savePassword} className="space-y-4">
            <Field label="Current password" htmlFor="cur_pw">
              <Input
                id="cur_pw"
                type="password"
                autoComplete="current-password"
                value={pw.current}
                onChange={(e) => setPw({ ...pw, current: e.target.value })}
                required
              />
            </Field>
            <Field label="New password" htmlFor="new_pw">
              <Input
                id="new_pw"
                type="password"
                autoComplete="new-password"
                value={pw.next}
                onChange={(e) => setPw({ ...pw, next: e.target.value })}
                required
              />
            </Field>
            <Field label="Confirm new password" htmlFor="confirm_pw">
              <Input
                id="confirm_pw"
                type="password"
                autoComplete="new-password"
                value={pw.confirm}
                onChange={(e) => setPw({ ...pw, confirm: e.target.value })}
                required
              />
            </Field>
            <Button type="submit" size="sm" disabled={savingPw}>
              {savingPw ? "Updating…" : "Update password"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Change email</CardTitle>
          <CardDescription>
            We email a confirmation link to the new address. The change only takes effect once you
            click it, and it signs out your other sessions.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={requestEmail} className="space-y-4">
            <Field label="New email address" htmlFor="new_email">
              <Input
                id="new_email"
                type="email"
                value={em.email}
                onChange={(e) => setEm({ ...em, email: e.target.value })}
                required
              />
            </Field>
            <Field label="Current password" htmlFor="em_pw">
              <Input
                id="em_pw"
                type="password"
                autoComplete="current-password"
                value={em.password}
                onChange={(e) => setEm({ ...em, password: e.target.value })}
                required
              />
            </Field>
            <Button type="submit" size="sm" disabled={savingEm}>
              {savingEm ? "Sending…" : "Send confirmation link"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
