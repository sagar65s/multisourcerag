"use client";

import {
  browserLocalPersistence,
  browserSessionPersistence,
  GoogleAuthProvider,
  setPersistence,
  signInWithEmailAndPassword,
  signInWithPopup,
} from "firebase/auth";
import { ArrowRight, Eye, EyeOff, LockKeyhole } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { BrandMark } from "@/components/brand/mark";
import { AuthTriangleField } from "@/components/animations/auth-triangle-field";
import { Button } from "@/components/ui/button";
import { getFirebaseAuth } from "@/lib/firebase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [remember, setRemember] = useState(true);

  const destination = () => {
    const requested = new URLSearchParams(window.location.search).get("next");
    return requested?.startsWith("/") && !requested.startsWith("//")
      ? requested
      : "/dashboard";
  };
  const configurePersistence = () =>
    setPersistence(
      getFirebaseAuth(),
      remember ? browserLocalPersistence : browserSessionPersistence,
    );

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await configurePersistence();
      await signInWithEmailAndPassword(getFirebaseAuth(), email, password);
      router.replace(destination());
    } catch {
      setError(
        "Login failed. Check your email, password, and Firebase configuration.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function google() {
    setBusy(true);
    setError("");
    try {
      await configurePersistence();
      await signInWithPopup(getFirebaseAuth(), new GoogleAuthProvider());
      router.replace(destination());
    } catch {
      setError("Google sign-in could not be completed.");
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
        <span className="eyebrow">
          <LockKeyhole size={15} /> Your private intelligence space
        </span>
        <h1>
          Research deeply.
          <br />
          <span>Stay in control.</span>
        </h1>
        <p>
          Bring your documents and trusted web sources together without giving
          up ownership of your knowledge.
        </p>
        <div className="auth-proof">
          <div>
            <strong>Scoped</strong>
            <span>Every retrieval</span>
          </div>
          <div>
            <strong>Verified</strong>
            <span>Every identity</span>
          </div>
          <div>
            <strong>Cited</strong>
            <span>Every answer</span>
          </div>
        </div>
      </section>
      <form className="auth-card" onSubmit={submit}>
        <div>
          <span className="auth-kicker">WELCOME BACK</span>
          <h2>Continue your research</h2>
          <p>Sign in to your private knowledge workspace.</p>
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
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </label>
        <label>
          Password
          <div className="password-input">
            <input
              type={visible ? "text" : "password"}
              autoComplete="current-password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
            />
            <button
              type="button"
              onClick={() => setVisible(!visible)}
              aria-label={visible ? "Hide password" : "Show password"}
            >
              {visible ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </label>
        <div className="form-meta">
          <label className="check-label">
            <input
              type="checkbox"
              checked={remember}
              onChange={(event) => setRemember(event.target.checked)}
            />{" "}
            Remember me
          </label>
          <Link href="/forgot-password">Forgot password?</Link>
        </div>
        <Button type="submit" size="lg" disabled={busy}>
          {busy ? (
            "Signing in…"
          ) : (
            <>
              Sign in <ArrowRight size={18} />
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
          New to MultiSource AI? <Link href="/register">Create an account</Link>
        </p>
      </form>
    </main>
  );
}
