import { spawnSync } from "node:child_process";
import { checkChromium } from "./check-playwright-browser.mjs";

const configuredBrowsers = process.env.E2E_COMPAT_BROWSERS || "chromium";
const projects = ["compatibility-chromium"];
const compatibilitySpecs = [
  "e2e/smoke.spec.ts",
  "e2e/pds-runtime-csp.spec.ts",
  "e2e/pds-scheme-dark.spec.ts",
  "e2e/memory-conflict.spec.ts",
];

if (configuredBrowsers.trim() !== "chromium") {
  console.error("E2E_COMPAT_BROWSERS must be chromium.");
  process.exit(1);
}

if (!(await checkChromium())) {
  process.exit(1);
}

const forwardedArgs = process.argv.slice(2);
const result = spawnSync(
  "playwright",
  [
    "test",
    "--config=playwright.compat.config.ts",
    ...projects.map((project) => `--project=${project}`),
    ...(forwardedArgs.length > 0 ? forwardedArgs : compatibilitySpecs),
  ],
  {
    stdio: "inherit",
  },
);

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
