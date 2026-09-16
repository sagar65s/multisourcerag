"use client";

import { Menu, Search } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";

import { Sidebar } from "@/components/layout/sidebar";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);
  const path = usePathname();
  const router = useRouter();
  useEffect(() => setOpen(false), [path]);
  useEffect(() => {
    const keyboard = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", keyboard);
    return () => document.removeEventListener("keydown", keyboard);
  }, []);
  const search = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = query.trim();
    router.push(value ? `/history?q=${encodeURIComponent(value)}` : "/history");
  };
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <button type="button" className={open ? "mobile-scrim visible" : "mobile-scrim"} onClick={() => setOpen(false)} aria-label="Close navigation" tabIndex={open ? 0 : -1} />
      <div className={open ? "sidebar-wrap open" : "sidebar-wrap"}><Sidebar /></div>
      <div className="app-column">
        <header className="topbar">
          <Button variant="ghost" size="icon" className="mobile-menu" onClick={() => setOpen(true)} aria-label="Open navigation" aria-expanded={open}><Menu size={19} /></Button>
          <form className="top-search" role="search" onSubmit={search}>
            <Search size={18} aria-hidden="true" />
            <input ref={searchRef} value={query} onChange={(event) => setQuery(event.target.value)} aria-label="Search chats and research" placeholder="Search your history…" />
            <kbd aria-hidden="true">Ctrl K</kbd>
          </form>
          <div className="top-actions"><ThemeToggle /><Link className="avatar" href="/settings" aria-label="Open account settings">MS</Link></div>
        </header>
        <main className="app-content" id="main-content" tabIndex={-1}>{children}</main>
      </div>
    </div>
  );
}
