"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { BrandMark } from "@/components/brand/mark";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";

export function LandingNav() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const close = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, []);
  const close = () => setOpen(false);
  return (
    <header className="landing-nav">
      <Link className="brand" href="/" aria-label="MultiSource AI home"><BrandMark /><span>MultiSource <span>AI</span></span></Link>
      <nav className="landing-desktop-nav" aria-label="Main navigation"><a href="#capabilities">Capabilities</a><a href="#security">Security</a><a href="#workflow">How it works</a></nav>
      <div className="nav-actions"><ThemeToggle /><button className="landing-menu-trigger" type="button" aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open} aria-controls="landing-mobile-navigation" onClick={() => setOpen((value) => !value)}>{open ? <X size={18} /> : <Menu size={18} />}</button><Button asChild size="sm"><Link href="/login">Get started</Link></Button></div>
      {open && <><button className="landing-mobile-scrim" aria-label="Close menu" onClick={close} /><nav id="landing-mobile-navigation" className="landing-mobile-nav" aria-label="Mobile navigation"><a href="#capabilities" onClick={close}>Capabilities</a><a href="#security" onClick={close}>Security</a><a href="#workflow" onClick={close}>How it works</a></nav></>}
    </header>
  );
}
