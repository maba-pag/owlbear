const { createRequire } = require("node:module");
const path = require("node:path");

const requireCockpitPackage = createRequire(
  path.resolve(__dirname, "serve/cockpit/web/package.json"),
);
const jsonModule = requireCockpitPackage("@eslint/json");
const json = jsonModule.default ?? jsonModule;

const rootAndNestedDirectories = [
  ".benchmarks/**",
  "**/.benchmarks/**",
  ".ruff_cache/**",
  "**/.ruff_cache/**",
  ".venv/**",
  "**/.venv/**",
  "__pycache__/**",
  "**/__pycache__/**",
  "_cache/**",
  "**/_cache/**",
  "artifacts/**",
  "**/artifacts/**",
  "build/**",
  "**/build/**",
  "coverage/**",
  "**/coverage/**",
  "dist/**",
  "**/dist/**",
  "downloads/**",
  "**/downloads/**",
  "htmlcov/**",
  "**/htmlcov/**",
  "node_modules/**",
  "**/node_modules/**",
  "parts/**",
  "**/parts/**",
  "playwright-report/**",
  "**/playwright-report/**",
  "scratch/**",
  "**/scratch/**",
  "sdist/**",
  "**/sdist/**",
  "test-results/**",
  "**/test-results/**",
  "wheels/**",
  "**/wheels/**",
  "worktrees/**",
  "**/worktrees/**",
  "megalinter-reports/**",
  "**/megalinter-reports/**",
];


const ignores = [
  "*.egg-info/**",
  "**/*.egg-info/**",
  ".owlbear/delivery/packages/**",
  "**/.owlbear/delivery/packages/**",
  ".owlbear/delivery/runtime/**",
  "**/.owlbear/delivery/runtime/**",
  ".owlbear/memory/**",
  "**/.owlbear/memory/**",
  ".owlbear/research/**",
  "**/.owlbear/research/**",
  ".owlbear/sources/**",
  "**/.owlbear/sources/**",
  "store/audit/*.db",
  "store/knowledge/*.db",
  ...rootAndNestedDirectories,
];

const duplicateKeyRules = {
  "json/no-duplicate-keys": "error",
};

module.exports = [
  { ignores },
  {
    files: ["**/*.json"],
    plugins: { json },
    language: "json/json",
    rules: duplicateKeyRules,
  },
  {
    files: ["**/*.jsonc", ".vscode/*.json"],
    plugins: { json },
    language: "json/jsonc",
    languageOptions: { allowTrailingCommas: true },
    rules: duplicateKeyRules,
  },
];
