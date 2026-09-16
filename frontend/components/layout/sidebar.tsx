"use client";

import {
  Archive,
  Clock3,
  FileStack,
  FlaskConical,
  Globe2,
  Home,
  MessageSquareText,
  Settings,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getAuthenticatedUser } from "@/lib/firebase";

import { BrandMark } from "@/components/brand/mark";
import { cn } from "@/lib/utils";

const items = [
  ["Dashboard", "/dashboard", Home],
  ["Chat", "/chat", MessageSquareText],
  ["Documents", "/documents", FileStack],
  ["Websites", "/websites", Globe2],
  ["Research", "/research", FlaskConical],
  ["Saved", "/saved", Archive],
  ["History", "/history", Clock3],
] as const;

const primaryItems = items.slice(0, 5);
const libraryItems = items.slice(5);

export function Sidebar() {
  const path = usePathname();
  const [isAdmin, setIsAdmin] = useState(false);
  useEffect(() => {
    void getAuthenticatedUser()
      .then(async (user) => {
        const token = user ? await user.getIdTokenResult() : null;
        setIsAdmin(Boolean(token?.claims.admin));
      })
      .catch(() => setIsAdmin(false));
  }, [path]);
  return (
    <aside className="sidebar">
      <Link className="brand sidebar-brand" href="/">
        <BrandMark />
        <span>
          MultiSource <span>AI</span>
        </span>
      </Link>
      <Link className="new-chat" href="/chat">
        <MessageSquareText size={18} aria-hidden="true" /> New chat
      </Link>
      <nav aria-label="Main navigation">
        <span className="nav-group-label">Explore</span>
        {primaryItems.map(([label, href, Icon]) => (
          <Link
            key={href}
            className={cn("side-link", path === href && "active")}
            href={href}
            aria-current={path === href ? "page" : undefined}
          >
            <Icon size={19} aria-hidden="true" />
            <span>{label}</span>
          </Link>
        ))}
        <span className="nav-group-label nav-group-space">Your library</span>
        {libraryItems.map(([label, href, Icon]) => (
          <Link key={href} className={cn("side-link", path === href && "active")} href={href} aria-current={path === href ? "page" : undefined}>
            <Icon size={19} aria-hidden="true" /><span>{label}</span>
          </Link>
        ))}
      </nav>
      {isAdmin && (
        <Link
          className={cn("side-link admin-link", path === "/admin" && "active")}
          href="/admin"
        >
          <ShieldCheck size={18} />
          <span>Admin</span>
        </Link>
      )}
      <div className="sidebar-bottom">
        <Link className="side-link" href="/settings">
          <Settings size={18} />
          <span>Settings</span>
        </Link>
      </div>
    </aside>
  );
}
