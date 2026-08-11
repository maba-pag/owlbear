import { spawnSync } from "node:child_process";
import { checkChromium } from "./check-playwright-browser.mjs";

const fastGateSpecs = [
  "e2e/smoke.spec.ts",
  "e2e/pds-runtime-csp.spec.ts",
];

const forwardedArgs = process.argv.slice(2);
const playwrightArgs = forwardedArgs.length === 0 ? fastGateSpecs : forwardedArgs;

if (!(await checkChromium())) {
  process.exit(1);
}

const result = spawnSync("playwright", ["test", ...playwrightArgs], {
  shell: process.platform === "win32",
  stdio: "inherit",
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 1);
