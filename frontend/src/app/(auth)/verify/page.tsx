"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { apiFetch, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type State = "working" | "ok" | "error";

export default function VerifyPage() {
  return (
    <Suspense fallback={<Card className="h-40" />}>
      <VerifyInner />
    </Suspense>
  );
}

function VerifyInner() {
  const token = useSearchParams().get("token");
  const [state, setState] = useState<State>("working");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setState("error");
      setMessage("This link is missing its token.");
      return;
    }
    apiFetch<void>("/auth/verify-email", { method: "POST", json: { token } })
      .then(() => setState("ok"))
      .catch((e) => {
        setState("error");
        setMessage(e instanceof ApiError ? e.message : "Verification failed.");
      });
  }, [token]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {state === "working" && "Verifying…"}
          {state === "ok" && "Email confirmed"}
          {state === "error" && "Verification failed"}
        </CardTitle>
        <CardDescription>
          {state === "ok" ? "Your address is confirmed. You can sign in." : message}
        </CardDescription>
      </CardHeader>
      {state !== "working" && (
        <CardContent>
          <Button asChild className="w-full">
            <Link href="/login">Go to sign in</Link>
          </Button>
        </CardContent>
      )}
    </Card>
  );
}
