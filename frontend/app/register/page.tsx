"use client";

import {
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  signInWithPopup,
} from "firebase/auth";
import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { BrandMark } from "@/components/brand/mark";
import { AuthTriangleField } from "@/components/animations/auth-triangle-field";
import { Button } from "@/components/ui/button";
import { getFirebaseAuth } from "@/lib/firebase";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function register(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await createUserWithEmailAndPassword(getFirebaseAuth(), email, password);
      router.push("/dashboard");
    } catch {
      setError(
        "Account creation failed. Use a valid email and a stronger password.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function google() {
    setBusy(true);
    setError("");
    try {
      await signInWithPopup(getFirebaseAuth(), new GoogleAuthProvider());
      router.push("/dashboard");
    } catch {
      setError("Google sign-up could not be completed.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="auth-page">
      <AuthTriangleField />
      <Link href="/" className="auth-brand">
        <BrandMark /> MultiSource AI
      </Link>
      <section className="auth-story">
        <span className="eyebrow">△ PRIVATE BY DEFAULT</span>
        <h1>
          Build knowledge.
          <br />
          <span>Keep ownership.</span>
        </h1>
        <p>
          Create isolated workspaces for your documents, websites, research and
          source-grounded conversations.
        </p>
      </section>
      <form className="auth-card" onSubmit={register}>
        <div>
          <span className="auth-kicker">CREATE ACCOUNT</span>
          <h2>Begin securely</h2>
          <p>
            Your sources are private unless you explicitly choose otherwise.
          </p>
        </div>
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}
        <label>
          Email address
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
          />
        </label>
        <Button size="lg" type="submit" disabled={busy}>
          {busy ? (
            "Creating…"
          ) : (
            <>
              Create account <ArrowRight size={18} />
            </>
          )}
        </Button>
        <div className="or">
          <span />
          or
          <span />
        </div>
        <Button
          type="button"
          variant="secondary"
          size="lg"
          onClick={google}
          disabled={busy}
        >
          Continue with Google
        </Button>
        <p className="auth-switch">
          Already have an account? <Link href="/login">Sign in</Link>
        </p>
      </form>
    </main>
  );
}
