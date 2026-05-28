/**
 * Export .excalidraw files to PNG using Playwright + @excalidraw/utils.
 *
 * Renders each file in headless Chromium via @excalidraw/utils (loaded from
 * esm.sh CDN), then screenshots the resulting SVG element.
 *
 * Usage:
 *   node export.mjs <input.excalidraw> [output.png]
 *   node export.mjs --all [diagrams-dir]
 *
 * Environment:
 *   EXCALIDRAW_SCALE  Device scale factor (default: 1)
 *
 * Setup (one-time):
 *   cd .owlbear/scripts/export-diagrams && npm install && npx playwright install chromium
 */

import { chromium } from "playwright";
import { readFileSync, writeFileSync, readdirSync } from "fs";
import { resolve, basename, dirname, join } from "path";
import { fileURLToPath, pathToFileURL } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const RENDER_HTML = join(__dirname, "render.html");
const DEVICE_SCALE = parseInt(process.env.EXCALIDRAW_SCALE || "1", 10);
const WORKSPACE_ROOT = resolve(__dirname, "../../..");
const DEFAULT_DIAGRAMS_DIR = join(WORKSPACE_ROOT, "share/diagrams");

async function exportFile(page, inputPath, outputPath) {
  const data = JSON.parse(readFileSync(inputPath, "utf-8"));
  const dims = await page.evaluate((d) => window.renderExcalidraw(d), data);
  const root = await page.$("#root > svg");
  if (!root) {
    throw new Error(`No SVG rendered for ${inputPath}`);
  }
  const screenshot = await root.screenshot({ type: "png", scale: "device" });
  writeFileSync(outputPath, screenshot);
  console.log(`  ${basename(inputPath)} → ${basename(outputPath)} (${dims.width}×${dims.height})`);
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error("Usage: node export.mjs <file.excalidraw> [output.png]");
    console.error("       node export.mjs --all [diagrams-dir]");
    process.exit(1);
  }

  const allMode = args[0] === "--all";
  const browser = await chromium.launch();
  const context = await browser.newContext({ deviceScaleFactor: DEVICE_SCALE });
  const page = await context.newPage();
  await page.goto(pathToFileURL(RENDER_HTML).href);
  await page.waitForFunction(() => typeof window.renderExcalidraw === "function", {
    timeout: 30000,
  });

  try {
    if (allMode) {
      const dir = resolve(args[1] || DEFAULT_DIAGRAMS_DIR);
      const files = readdirSync(dir).filter((f) => f.endsWith(".excalidraw"));
      console.log(`Exporting ${files.length} diagrams from ${dir} (${DEVICE_SCALE}x):`);
      for (const f of files) {
        const input = join(dir, f);
        const output = join(dir, f.replace(/\.excalidraw$/, ".png"));
        await exportFile(page, input, output);
      }
    } else {
      const input = resolve(args[0]);
      const output = args[1] ? resolve(args[1]) : input.replace(/\.excalidraw$/, ".png");
      console.log(`Exporting (${DEVICE_SCALE}x):`);
      await exportFile(page, input, output);
    }
    console.log("Done.");
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
