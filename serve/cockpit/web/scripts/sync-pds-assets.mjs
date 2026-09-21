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

const OUTPUT_DIR =
  globalThis.process.env.PDS_OUTPUT_DIR ?? join(globalThis.process.cwd(), "public", "porsche-design-system");
const DOWNLOAD_CONCURRENCY = 8;

const CREST_FILES = [
  "porsche-crest.d76137c@1x.png",
  "porsche-crest.0d0cc89@1x.webp",
  "porsche-crest.8a292fb@2x.png",
  "porsche-crest.2245c45@2x.webp",
  "porsche-crest.18d6f02@3x.png",
  "porsche-crest.19b4292@3x.webp",
];

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

async function fetchBytes(url, context) {
  const response = await fetch(url);
  if (!response.ok) {
    fail(`cdn download failed (${context}): ${url} -> HTTP ${response.status}`);
  }
  return Buffer.from(await response.arrayBuffer());
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
  for (const pair of mapMatch[1].matchAll(pairRegex)) {
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
  const iconRegex = /(?:"([a-z0-9-]+)"|([a-z0-9-]+))\s*:\s*"([a-z0-9-]+\.[a-f0-9]+\.svg)"/gi;
  for (const iconMatch of iconSource.matchAll(iconRegex)) {
    const name = iconMatch[1] ?? iconMatch[2];
    const filename = iconMatch[3];
    entries.set(name, filename);
  }

  if (entries.size === 0) {
    fail("failed to parse icon filename map from icon chunk");
  }

  return entries;
}

async function downloadAssets(filenames, directory, baseUrl, fetchContent) {
  const pending = filenames.values();
  let failure;
  const worker = async () => {
    for (const filename of pending) {
      if (failure) return;
      try {
        const content = await fetchContent(`${baseUrl}/${filename}`, filename);
        await writeFile(join(directory, filename), content);
      } catch (error) {
        failure ??= error;
        return;
      }
    }
  };
  await Promise.all(Array.from({ length: Math.min(DOWNLOAD_CONCURRENCY, filenames.length) }, worker));
  if (failure) throw failure;
}

export async function syncPdsAssets({ indexPath = INDEX_MJS_PATH, outputDir = OUTPUT_DIR } = {}) {
  const componentsDir = join(outputDir, "components");
  const iconsDir = join(outputDir, "icons");
  const crestDir = join(outputDir, "crest");
  const indexSource = await readFile(indexPath, "utf8");
  const corePath = parseCorePath(indexSource);
  const cdnBase = "https://cdn.ui.porsche.com";

  for (const directory of [componentsDir, iconsDir, crestDir]) {
    await rm(directory, { recursive: true, force: true });
    await mkdir(directory, { recursive: true });
  }

  const coreSource = await fetchText(`${cdnBase}${corePath}`, "core chunk");
  const coreFilename = corePath.split("/").pop();
  if (!coreFilename) fail("failed to derive core chunk filename");
  await writeFile(join(componentsDir, coreFilename), coreSource, "utf8");

  const componentHashes = parseComponentHashes(coreSource);
  const componentFiles = [...componentHashes].map(([name, hash]) => `porsche-design-system.${name}.${hash}.js`);
  await downloadAssets(componentFiles, componentsDir, `${cdnBase}/porsche-design-system/components`, fetchText);

  const iconHash = componentHashes.get("icon");
  if (!iconHash) fail("failed to locate icon chunk in component chunk-map");
  const iconSource = await readFile(join(componentsDir, `porsche-design-system.icon.${iconHash}.js`), "utf8");
  const iconMap = parseIconFilenameMap(iconSource);
  await downloadAssets([...new Set(iconMap.values())], iconsDir, `${cdnBase}/porsche-design-system/icons`, fetchText);
  await downloadAssets(CREST_FILES, crestDir, `${cdnBase}/porsche-design-system/crest`, fetchBytes);

  console.log(
    `[sync-pds] synced ${componentHashes.size + 1} component files, ` +
      `${iconMap.size} icons, and ${CREST_FILES.length} crest assets`,
  );
}

if (import.meta.main) {
  syncPdsAssets().catch((error) => {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`[sync-pds] failed: ${message}`);
    globalThis.process.exitCode = 1;
  });
}
