import { spawnSync } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const packageRoot = fileURLToPath(new URL("..", import.meta.url));
const fixtureRoot = await mkdtemp(join(packageRoot, "src/biome-pds-"));
const invalidFixture = join(fixtureRoot, "invalid.tsx");
const validFixture = join(fixtureRoot, "valid.tsx");
const wrapperMessage = "Use the corresponding Porsche Design System React wrapper";
const invalidSource = [
  "export const Invalid = () => (",
  "  <>",
  '    <p-select data-testid="select" />',
  '    <p-button aria-label="button" />',
  '    <p-input-search value="query" />',
  '    <p-input-text value="text" />',
  '    <p-tag variant="info" />',
  '    <p-select value="one">Choose one</p-select>',
  '    <p-button type="submit">Continue</p-button>',
  '    <p-input-search name="query">Search</p-input-search>',
  '    <p-input-text name="text">Text</p-input-text>',
  '    <p-tag variant="success">Tag</p-tag>',
  "  </>",
  ");",
  "",
].join("\n");

const runBiome = (fixture) =>
  spawnSync(
    process.execPath,
    [join(packageRoot, "scripts/run-biome-check.mjs"), "lint", "--only=plugin", fixture, "--reporter=json"],
    { cwd: packageRoot, encoding: "utf8" },
  );

try {
  await writeFile(invalidFixture, invalidSource, "utf8");
  await writeFile(validFixture, `const PSelect = () => null;\nexport const Valid = () => <PSelect />;\n`, "utf8");

  const invalidResult = runBiome(invalidFixture);
  const invalidOutput = `${invalidResult.stdout}${invalidResult.stderr}`;
  const wrapperFindings = invalidOutput.split(wrapperMessage).length - 1;
  if (invalidResult.status === 0 || wrapperFindings !== 10) {
    throw new Error(`expected ten PDS findings, received ${wrapperFindings}`);
  }

  const validResult = runBiome(validFixture);
  if (validResult.status !== 0) {
    throw new Error(`valid wrapper fixture failed:\n${validResult.stdout}${validResult.stderr}`);
  }
} finally {
  await rm(fixtureRoot, { recursive: true, force: true });
}
