import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";

const read = (path) => readFileSync(resolve(process.cwd(), path), "utf8");
const shell = read("components/layout/app-shell.tsx");
const css = read("app/globals.css");
const history = read("app/(app)/history/page.tsx");
const appLayout = read("app/(app)/layout.tsx");
const authGuard = read("components/auth/auth-guard.tsx");
const login = read("app/login/page.tsx");
const packageManifest = JSON.parse(read("package.json"));
const apiClient = read("services/api.ts");
const settingsPage = read("app/(app)/settings/page.tsx");
const dashboardPage = read("app/(app)/dashboard/page.tsx");
const researchPage = read("app/(app)/research/page.tsx");
const adminPage = read("app/(app)/admin/page.tsx");
const jobService = read("services/job.service.ts");
const chat = read("components/chat/chat-experience.tsx");
const voiceHook = read("hooks/use-voice.ts");
const failures = [];

const requireText = (source, text, message) => {
  if (!source.includes(text)) failures.push(message);
};

requireText(shell, 'href="#main-content"', "Application shell needs a keyboard skip link.");
requireText(shell, 'id="main-content"', "Application shell needs a main-content focus target.");
requireText(shell, 'role="search"', "Global history search needs a search landmark.");
requireText(shell, 'aria-expanded={open}', "Mobile navigation trigger must expose expanded state.");
requireText(shell, 'aria-label="Close navigation"', "Mobile navigation overlay needs an accessible close action.");
requireText(history, 'aria-label="Search history"', "History filter needs an accessible name.");
requireText(css, "@media (prefers-reduced-motion: reduce)", "Reduced-motion overrides are required.");
requireText(css, "@media (pointer: coarse)", "Touch-target overrides are required for coarse pointers.");
requireText(css, "overflow-wrap: anywhere", "Long untrusted content needs overflow protection.");
requireText(appLayout, "<AuthGuard>", "Private application routes must mount behind the Firebase auth guard.");
requireText(authGuard, "onAuthStateChanged", "Auth guard must wait for Firebase's resolved session state.");
requireText(authGuard, "router.replace", "Unauthenticated private routes must redirect before mounting content.");
requireText(authGuard, "syncAccountSession", "Verified Firebase sessions must synchronize the private backend account profile.");
requireText(login, "browserLocalPersistence", "Remembered login must use durable Firebase persistence.");
requireText(login, "browserSessionPersistence", "Non-remembered login must end with the browser session.");
if (packageManifest.scripts?.start !== "node scripts/start-production.mjs") failures.push("Production start must use the standalone-compatible launcher.");
requireText(apiClient, "AbortController", "Authenticated API requests need bounded timeout and cancellation handling.");
requireText(apiClient, "Could not reach the secure API", "Network failures need a user-safe error message.");
requireText(settingsPage, "updateUserSettings", "User preferences must persist through the owner-scoped backend API.");
requireText(jobService, '/cancel', "Processing jobs need a real cancellation API action.");
requireText(jobService, '/retry', "Failed processing jobs need a real retry API action.");
requireText(dashboardPage, "job.can_cancel", "Dashboard must render cancellation only when the server allows it.");
requireText(dashboardPage, "job.can_retry", "Dashboard must render retry only when the server allows it.");
requireText(dashboardPage, 'className="collection-guide"', "Dashboard needs a prominent source-collection onboarding guide.");
requireText(css, "Final cascade guard", "Application pages need an app-wide readable typography floor.");
requireText(chat, "<span>Listen</span>", "Chat answer actions need visible, readable labels on larger screens.");
requireText(researchPage, 'downloadExport("research", active.id, "pdf")', "Completed research needs a direct PDF download action.");
requireText(adminPage, 'aria-label="API route health"', "Admin request observability table needs an accessible region label.");
requireText(adminPage, "data.operations", "Admin operations UI must use real backend observability data.");
requireText(chat, '"Listen to this answer"', "Each persisted AI answer needs its own accessible speech action.");
if (!/voice\.speak\(\s*message\.content/.test(chat)) failures.push("Answer speech must be scoped to the selected AI message.");
requireText(voiceHook, "speechChunks", "Long AI answers must be chunked to avoid browser speech hangs.");
requireText(voiceHook, "speechSynthesis.cancel()", "Answer speech must be cancellable during navigation and replay.");
requireText(voiceHook, '"ta-IN"', "Answer speech must support Tamil.");
requireText(voiceHook, '"hi-IN"', "Answer speech must support Hindi.");

const sourceFiles = (directory) => readdirSync(resolve(process.cwd(), directory), { withFileTypes: true }).flatMap((entry) => {
  const relative = `${directory}/${entry.name}`;
  return entry.isDirectory() ? sourceFiles(relative) : /\.(tsx|ts)$/.test(entry.name) ? [relative] : [];
});
const sourceBundle = [...sourceFiles("app"), ...sourceFiles("components")].map(read).join("\n");
// Browser alert() bypasses the accessible inline status and error system.
if (/\b(?:window\.)?alert\s*\(/.test(sourceBundle)) failures.push("Browser alert() is not permitted in core interaction flows.");

if (failures.length) {
  console.error(failures.map((item) => `- ${item}`).join("\n"));
  process.exit(1);
}
console.log("Accessibility contract audit passed (landmarks, keyboard navigation, motion, touch, and overflow safeguards).");
