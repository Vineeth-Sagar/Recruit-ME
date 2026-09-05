"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

const schema = z.object({
  full_name: z.string().min(1, "Required").max(200),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "At least 8 characters").max(200),
});
type FormValues = z.infer<typeof schema>;

export default function SignupPage() {
  const { signup, login } = useAuth();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    try {
      await signup(values.email, values.password, values.full_name);
      await login(values.email, values.password);
      window.location.assign("/dashboard");
    } catch (e) {
      if (e instanceof ApiError && e.code === "email_taken") {
        toast.error("That email is already registered");
        return;
      }
      toast.error(e instanceof ApiError ? e.message : "Could not create the account");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create your account</CardTitle>
        <CardDescription>
          A confirmation email is sent; you can start setting up right away.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Field label="Name" htmlFor="full_name" error={errors.full_name?.message}>
            <Input id="full_name" autoComplete="name" {...register("full_name")} />
          </Field>
          <Field label="Email" htmlFor="email" error={errors.email?.message}>
            <Input id="email" type="email" autoComplete="email" {...register("email")} />
          </Field>
          <Field label="Password" htmlFor="password" error={errors.password?.message}>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              {...register("password")}
            />
          </Field>
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Creating…" : "Create account"}
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="hover:text-foreground">
            Sign in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
