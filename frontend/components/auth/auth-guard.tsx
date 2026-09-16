"use client";

import { onAuthStateChanged } from "firebase/auth";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { type PropsWithChildren, useEffect, useRef, useState } from "react";

import { BrandMark } from "@/components/brand/mark";
import { Button } from "@/components/ui/button";
import { getFirebaseAuth } from "@/lib/firebase";
import { syncAccountSession } from "@/services/account.service";

type GuardState = "checking" | "authorized" | "configuration_error";

export function AuthGuard({ children }: PropsWithChildren) {
  const [state, setState] = useState<GuardState>("checking");
  const pathname = usePathname();
  const router = useRouter();
  const requestedPath = useRef(pathname);

  useEffect(() => {
    let unsubscribe: (() => void) | undefined;
    try {
      unsubscribe = onAuthStateChanged(
        getFirebaseAuth(),
        (user) => {
          if (user) {
            void syncAccountSession()
              .catch(() => undefined)
              .finally(() => setState("authorized"));
          }
          else {
            setState("checking");
            router.replace(`/login?next=${encodeURIComponent(requestedPath.current)}`);
          }
        },
        () => setState("configuration_error"),
      );
    } catch {
      setState("configuration_error");
    }
    return () => unsubscribe?.();
  }, [router]);

  if (state === "authorized") return children;
  if (state === "configuration_error") {
    return (
      <main className="auth-gate auth-gate-error">
        <BrandMark />
        <span>AUTHENTICATION UNAVAILABLE</span>
        <h1>Secure sign-in is not configured.</h1>
        <p>Check the public Firebase settings for this deployment, then retry.</p>
        <div>
          <Button onClick={() => window.location.reload()}>Retry configuration</Button>
          <Button asChild variant="secondary"><Link href="/">Return home</Link></Button>
        </div>
      </main>
    );
  }
  return (
    <main className="auth-gate" role="status" aria-live="polite">
      <div className="triangle-loader" aria-hidden="true"><span /><span /><span /></div>
      <strong>Verifying your private session</strong>
      <span>Authentication is checked before workspace content loads.</span>
    </main>
  );
}
