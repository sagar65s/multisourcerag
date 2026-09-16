import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  outputDir: "./test-results",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [["line"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  expect: { timeout: 8_000, toHaveScreenshot: { animations: "disabled", caret: "hide", maxDiffPixelRatio: 0.015 } },
  use: {
    baseURL: "http://app.local",
    colorScheme: "dark",
    locale: "en-IN",
    timezoneId: "Asia/Kolkata",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "mobile", use: { ...devices["iPhone 13"], browserName: "chromium", viewport: { width: 390, height: 844 } } },
    { name: "tablet", use: { ...devices["iPad (gen 7)"], browserName: "chromium", viewport: { width: 810, height: 1080 } } },
    { name: "desktop", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } },
  ],
});
