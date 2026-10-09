import { constants } from "node:fs";
import { access } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

export async function checkChromium() {
  const browserName = "chromium";
  const browserType = chromium;
  const executablePath = browserType.executablePath();
  try {
    await access(executablePath, constants.X_OK);
    return true;
  } catch {
    console.error(
      [
        `Playwright ${browserName} is unavailable.`,
        `Expected executable: ${executablePath}`,
        "Install it from serve/cockpit/web with:",
        `  npx playwright install ${browserName}`,
      ].join("\n"),
    );
    return false;
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const requestedBrowsers = process.argv.slice(2);
  if (requestedBrowsers.some((browserName) => browserName !== "chromium")) {
    console.error("Only Chromium is supported.");
    process.exitCode = 1;
  } else {
    process.exitCode = (await checkChromium()) ? 0 : 1;
  }
}
