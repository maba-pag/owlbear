import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const eslintCli = resolve(root, "serve/cockpit/web/node_modules/eslint/bin/eslint.js");
const result = spawnSync(
  process.execPath,
  [
    eslintCli,
    "--config",
    "eslint-json.config.cjs",
    "--no-warn-ignored",
    "**/*.json",
    "**/*.jsonc",
  ],
  { cwd: root, stdio: "inherit" },
);

if (result.error) {
  console.error(result.error.message);
  process.exitCode = 1;
} else {
  process.exitCode = result.status ?? 1;
}
