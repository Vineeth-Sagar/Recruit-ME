"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api";
import { accountApi } from "@/lib/settings";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

type State = "working" | "ok" | "error";

export default function ConfirmEmailChangePage() {
  return (
    <Suspense fallback={<Card className="h-40" />}>
      <ConfirmInner />
    </Suspense>
  );
}

function ConfirmInner() {
  const token = useSearchParams().get("token");
  const [state, setState] = useState<State>("working");
  const [message, setMessage] = useState("");
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    if (!token) {
      setState("error");
      setMessage("This link is missing its token.");
      return;
    }
    accountApi
      .confirmEmailChange(token)
      .then(() => setState("ok"))
      .catch((e) => {
        setState("error");
        setMessage(e instanceof ApiError ? e.message : "The email change could not be confirmed.");
      });
  }, [token]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {state === "working" && "Confirming…"}
          {state === "ok" && "Email updated"}
          {state === "error" && "Couldn't confirm"}
        </CardTitle>
        <CardDescription>
          {state === "ok"
            ? "Your address is changed and your other sessions were signed out. Sign in again with the new email."
            : state === "error"
              ? message
              : "Applying your new email address."}
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
