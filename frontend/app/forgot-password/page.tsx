"use client";

import { sendPasswordResetEmail } from "firebase/auth";
import Link from "next/link";
import { FormEvent, useState } from "react";
import { BrandMark } from "@/components/brand/mark";
import { AuthTriangleField } from "@/components/animations/auth-triangle-field";
import { Button } from "@/components/ui/button";
import { getFirebaseAuth } from "@/lib/firebase";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "busy" | "sent" | "error">(
    "idle",
  );
  async function submit(event: FormEvent) {
    event.preventDefault();
    setState("busy");
    try {
      await sendPasswordResetEmail(getFirebaseAuth(), email);
      setState("sent");
    } catch {
      setState("error");
    }
  }
  return (
    <main className="auth-page">
      <AuthTriangleField />
      <Link href="/" className="auth-brand">
        <BrandMark /> MultiSource AI
      </Link>
      <section className="auth-story">
        <span className="eyebrow">△ ACCOUNT RECOVERY</span>
        <h1>
          Return to your
          <br />
          <span>private workspace.</span>
        </h1>
        <p>
          Firebase securely handles the password reset flow without exposing
          account credentials to this application.
        </p>
      </section>
      <form className="auth-card" onSubmit={submit}>
        <div>
          <span className="auth-kicker">PASSWORD RESET</span>
          <h2>Recover your account</h2>
          <p>We’ll send a secure reset link if the account exists.</p>
        </div>
        {state === "sent" && (
          <div className="private-chip">
            Reset email requested. Check your inbox.
          </div>
        )}
        {state === "error" && (
          <div className="form-error">
            The reset request could not be completed.
          </div>
        )}
        <label>
          Email address
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
          />
        </label>
        <Button size="lg" disabled={state === "busy"}>
          {state === "busy" ? "Sending…" : "Send reset link"}
        </Button>
        <p className="auth-switch">
          <Link href="/login">Back to sign in</Link>
        </p>
      </form>
    </main>
  );
}
