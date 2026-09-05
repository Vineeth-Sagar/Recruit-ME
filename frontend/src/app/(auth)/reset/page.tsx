"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { apiFetch, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

const requestSchema = z.object({ email: z.string().email("Enter a valid email") });
const resetSchema = z.object({ password: z.string().min(8, "At least 8 characters").max(200) });

export default function ResetPage() {
  return (
    <Suspense fallback={<Card className="h-56" />}>
      <ResetInner />
    </Suspense>
  );
}

function ResetInner() {
  const token = useSearchParams().get("token");
  return token ? <ChooseNewPassword token={token} /> : <RequestLink />;
}

function RequestLink() {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isSubmitSuccessful },
  } = useForm<z.infer<typeof requestSchema>>({ resolver: zodResolver(requestSchema) });

  async function onSubmit(values: z.infer<typeof requestSchema>) {
    await apiFetch<void>("/auth/forgot", { method: "POST", json: values });
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Reset password</CardTitle>
        <CardDescription>
          {isSubmitSuccessful
            ? "If that address has an account, a reset link is on its way."
            : "Enter your email and we'll send a reset link."}
        </CardDescription>
      </CardHeader>
      {!isSubmitSuccessful && (
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Field label="Email" htmlFor="email" error={errors.email?.message}>
              <Input id="email" type="email" autoComplete="email" {...register("email")} />
            </Field>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Sending…" : "Send reset link"}
            </Button>
          </form>
        </CardContent>
      )}
    </Card>
  );
}

function ChooseNewPassword({ token }: { token: string }) {
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isSubmitSuccessful },
  } = useForm<z.infer<typeof resetSchema>>({ resolver: zodResolver(resetSchema) });

  async function onSubmit(values: z.infer<typeof resetSchema>) {
    try {
      await apiFetch<void>("/auth/reset", {
        method: "POST",
        json: { token, password: values.password },
      });
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Could not reset the password");
      throw e;
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Choose a new password</CardTitle>
        <CardDescription>
          {isSubmitSuccessful ? "Password updated. You can sign in now." : "Pick something strong."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isSubmitSuccessful ? (
          <Button asChild className="w-full">
            <Link href="/login">Go to sign in</Link>
          </Button>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Field label="New password" htmlFor="password" error={errors.password?.message}>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                {...register("password")}
              />
            </Field>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : "Update password"}
            </Button>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
