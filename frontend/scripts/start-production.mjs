import { cpSync, existsSync, mkdirSync } from "node:fs";
import { spawn } from "node:child_process";
import { resolve } from "node:path";

const root = process.cwd();
const standalone = resolve(root, ".next/standalone");
const server = resolve(standalone, "server.js");
if (!existsSync(server)) {
  console.error("Production server is missing. Run npm run build first.");
  process.exit(1);
}

mkdirSync(resolve(standalone, ".next"), { recursive: true });
cpSync(resolve(root, ".next/static"), resolve(standalone, ".next/static"), { recursive: true });
if (existsSync(resolve(root, "public"))) {
  cpSync(resolve(root, "public"), resolve(standalone, "public"), { recursive: true });
}

const child = spawn(process.execPath, [server], {
  cwd: standalone,
  env: process.env,
  stdio: "inherit",
});
let shuttingDown = false;
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => {
    if (shuttingDown) return;
    shuttingDown = true;
    child.kill(signal);
    setTimeout(() => {
      child.kill("SIGKILL");
      process.exit(1);
    }, 5_000).unref();
  });
}
child.on("exit", (code) => {
  process.exit(shuttingDown ? 0 : (code ?? 1));
});
