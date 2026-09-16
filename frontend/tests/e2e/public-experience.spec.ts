import { expect, test } from "@playwright/test";
import { access } from "node:fs/promises";
import { extname, resolve } from "node:path";

const appOutput = resolve(process.cwd(), ".next/server/app");
const staticOutput = resolve(process.cwd(), ".next/static");
const publicRoutes: Record<string, string> = {
  "/": "index.html",
  "/login": "login.html",
  "/register": "register.html",
  "/forgot-password": "forgot-password.html",
  "/dashboard": "dashboard.html",
};
const contentTypes: Record<string, string> = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
};

async function expectNoHorizontalOverflow(page: import("@playwright/test").Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
}

test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce", colorScheme: "dark" });
  await page.addInitScript(() => {
    localStorage.setItem("theme", "dark");
  });
  await page.context().route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== "http://app.local") return route.abort("blockedbyclient");
    let filePath: string | undefined;
    if (url.pathname.startsWith("/_next/static/")) {
      const relative = url.pathname.slice("/_next/static/".length);
      if (!relative.includes("..")) filePath = resolve(staticOutput, relative);
    } else if (publicRoutes[url.pathname]) {
      filePath = resolve(appOutput, publicRoutes[url.pathname]);
    }
    if (!filePath || (!filePath.startsWith(appOutput) && !filePath.startsWith(staticOutput))) return route.fulfill({ status: 404, body: "Not found" });
    try {
      await access(filePath);
      return route.fulfill({ path: filePath, contentType: contentTypes[extname(filePath)] ?? "application/octet-stream" });
    } catch {
      return route.fulfill({ status: 404, body: "Not found" });
    }
  });
});

test("landing page is navigable, responsive, and visually stable", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: /One place for every source/i })).toBeVisible();
  await expect(page.getByRole("article")).toHaveCount(4);
  await expect(page.getByRole("link", { name: "MultiSource AI home" })).toHaveAttribute("href", "/");
  await expectNoHorizontalOverflow(page);
  await expect(page).toHaveScreenshot("landing-page.png", { fullPage: true });

  if (testInfo.project.name === "mobile") {
    const menu = page.getByRole("button", { name: "Open menu" });
    await expect(menu).toBeVisible();
    await menu.click();
    await expect(page.getByRole("button", { name: "Close menu" }).first()).toHaveAttribute("aria-expanded", "true");
    await expect(page.getByRole("navigation", { name: "Mobile navigation" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("navigation", { name: "Mobile navigation" })).toHaveCount(0);
  }

  await page.getByRole("link", { name: "See features" }).click();
  await expect(page).toHaveURL(/#capabilities$/);
  await expect(page.getByRole("heading", { name: "Simple tools. Strong answers." })).toBeInViewport();
});

test("authentication controls work without exposing protected content", async ({ page }) => {
  await page.goto("/login");
  const password = page.locator('input[autocomplete="current-password"]');
  await expect(password).toHaveAttribute("type", "password");
  await page.getByRole("button", { name: "Show password" }).click();
  await expect(password).toHaveAttribute("type", "text");
  await expect(page.getByRole("link", { name: "Forgot password?" })).toHaveAttribute("href", "/forgot-password");
  await expect(page.getByRole("link", { name: "Create an account" })).toHaveAttribute("href", "/register");
  await expectNoHorizontalOverflow(page);
  await expect(page).toHaveScreenshot("login-page.png", { fullPage: true });

  await page.goto("/dashboard");
  await expect(page.getByText(/Secure sign-in is not configured|Verifying your private session/i)).toBeVisible();
  await expect(page.getByText("Welcome back", { exact: false })).toHaveCount(0);
});

test("light theme remains responsive and visually stable", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("theme", "light"));
  await page.goto("/");
  await expect(page.locator("html")).toHaveClass(/light/);
  await expectNoHorizontalOverflow(page);
  await expect(page).toHaveScreenshot("landing-light-page.png", { fullPage: true });
});
