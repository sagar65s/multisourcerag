"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const [ready, setReady] = useState(false);
  useEffect(() => setReady(true), []);
  return (
    <Button variant="ghost" size="icon" aria-label="Toggle color theme" disabled={!ready} onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}>
      {ready && resolvedTheme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
    </Button>
  );
}

