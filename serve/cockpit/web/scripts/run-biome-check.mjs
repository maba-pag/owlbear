import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(packageRoot, "../../..");
const biome = resolve(packageRoot, "node_modules/.bin/biome");
const targets = [
  "serve/cockpit/web/src",
  "serve/cockpit/web/e2e",
  ".github/renovate.json",
  ".github/sync-manifest.json",
  ".markdownlint-cli2.jsonc",
  ".markdownlint.json",
  "package.json",
  "serve/cockpit/web/package.json",
  "serve/cockpit/web/tsconfig.json",
  "serve/cockpit/web/tsconfig.e2e.json",
  "serve/cockpit/web/.stylelintrc.json",
];

const result = spawnSync(biome, ["check", ...targets], {
  cwd: repositoryRoot,
  stdio: "inherit",
});

if (result.error) {
  throw result.error;
}

process.exitCode = result.status ?? 1;
