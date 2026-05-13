import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";

const INDEX_MJS_PATH = join(
  globalThis.process.cwd(),
  "node_modules",
  "@porsche-design-system",
  "components-js",
  "esm",
  "index.mjs",
);

const COMPONENTS_DIR = join(
  globalThis.process.cwd(),
  "public",
  "porsche-design-system",
  "components",
);
const ICONS_DIR = join(
  globalThis.process.cwd(),
  "public",
  "porsche-design-system",
  "icons",
);

function fail(message) {
  throw new Error(`[sync-pds] ${message}`);
}

async function fetchText(url, context) {
  const response = await fetch(url);
  if (!response.ok) {
    fail(`cdn download failed (${context}): ${url} -> HTTP ${response.status}`);
  }
  return response.text();
}

function parseCorePath(indexSource) {
  const match = indexSource.match(
    /cdn\.url\+"(\/porsche-design-system\/components\/porsche-design-system\.v[0-9]+\.[0-9]+\.[0-9]+\.[a-f0-9]+\.js)"/,
  );
  if (!match) {
    fail("failed to parse core chunk URL from index.mjs (cdn/chunk-map parse)");
  }
  return match[1];
}

function parseComponentHashes(coreSource) {
  const mapMatch = coreSource.match(/\.u=e=>"porsche-design-system\."\+e\+"\."\+\{([\s\S]*?)\}\[e\]\+"\.js"/);
  if (!mapMatch) {
    fail("failed to parse component chunk-map from core chunk");
  }

  const hashes = new Map();
  const pairRegex = /(?:"([a-z0-9-]+)"|([a-z0-9-]+))\s*:\s*"([a-f0-9]+)"/gi;
  let pair;
  while ((pair = pairRegex.exec(mapMatch[1])) !== null) {
    const name = pair[1] ?? pair[2];
    const hash = pair[3];
    hashes.set(name, hash);
  }

  if (hashes.size === 0) {
    fail("component chunk-map parse produced zero entries");
  }

  return hashes;
}

function parseIconFilenameMap(iconSource) {
  const entries = new Map();
  const iconRegex =
    /(?:"([a-z0-9-]+)"|([a-z0-9-]+))\s*:\s*"([a-z0-9-]+\.[a-f0-9]+\.svg)"/gi;
  let iconMatch;
  while ((iconMatch = iconRegex.exec(iconSource)) !== null) {
    const name = iconMatch[1] ?? iconMatch[2];
    const filename = iconMatch[3];
    entries.set(name, filename);
  }

  if (entries.size === 0) {
    fail("failed to parse icon filename map from icon chunk");
  }

  return entries;
}

async function resetOutputDirs() {
  await rm(COMPONENTS_DIR, { recursive: true, force: true });
  await rm(ICONS_DIR, { recursive: true, force: true });
  await mkdir(COMPONENTS_DIR, { recursive: true });
  await mkdir(ICONS_DIR, { recursive: true });
}

async function main() {
  try {
    const indexSource = await readFile(INDEX_MJS_PATH, "utf8");
    const corePath = parseCorePath(indexSource);
    const cdnBase = "https://cdn.ui.porsche.com";
    const coreUrl = `${cdnBase}${corePath}`;

    await resetOutputDirs();

    const coreSource = await fetchText(coreUrl, "core chunk");
    const coreFilename = corePath.split("/").pop();
    if (!coreFilename) {
      fail("failed to derive core chunk filename");
    }
    await writeFile(join(COMPONENTS_DIR, coreFilename), coreSource, "utf8");

    const componentHashes = parseComponentHashes(coreSource);
    for (const [chunkName, hash] of componentHashes.entries()) {
      const componentFilename = `porsche-design-system.${chunkName}.${hash}.js`;
      const componentUrl = `${cdnBase}/porsche-design-system/components/${componentFilename}`;
      const componentSource = await fetchText(componentUrl, `component chunk ${chunkName}`);
      await writeFile(join(COMPONENTS_DIR, componentFilename), componentSource, "utf8");
    }

    const iconHash = componentHashes.get("icon");
    if (!iconHash) {
      fail("failed to locate icon chunk in component chunk-map");
    }
    const iconChunkFilename = `porsche-design-system.icon.${iconHash}.js`;
    const iconChunkUrl = `${cdnBase}/porsche-design-system/components/${iconChunkFilename}`;
    const iconSource = await fetchText(iconChunkUrl, "icon chunk");
    const iconMap = parseIconFilenameMap(iconSource);

    for (const iconFilename of iconMap.values()) {
      const iconUrl = `${cdnBase}/porsche-design-system/icons/${iconFilename}`;
      const iconSvg = await fetchText(iconUrl, `icon ${iconFilename}`);
      await writeFile(join(ICONS_DIR, iconFilename), iconSvg, "utf8");
    }

    console.log(
      `[sync-pds] synced ${componentHashes.size + 1} component files and ${iconMap.size} icons`,
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`[sync-pds] failed: ${message}`);
    globalThis.process.exit(1);
  }
}

void main();
