import assert from "node:assert/strict";
import { mkdtemp, readdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
import { test } from "node:test";
import { setImmediate } from "node:timers/promises";
import { syncPdsAssets } from "./sync-pds-assets.mjs";

async function fixture(context) {
  const root = await mkdtemp(join(tmpdir(), "pds-sync-test-"));
  context.after(() => rm(root, { recursive: true, force: true }));
  const indexPath = join(root, "index.mjs");
  const coreName = "porsche-design-system.v4.6.0.abcdef.js";
  await writeFile(indexPath, `cdn.url+"/porsche-design-system/components/${coreName}"`);
  const componentNames = ["icon", ...Array.from({ length: 19 }, (_, index) => `component-${index}`)];
  const hashes = Object.fromEntries(componentNames.map((name) => [name, "abcdef"]));
  const core = `.u=e=>"porsche-design-system."+e+"."+${JSON.stringify(hashes)}[e]+".js"`;
  const icons = Object.fromEntries(
    Array.from({ length: 20 }, (_, index) => [`icon-${index}`, `symbol-${index}.abcdef.svg`]),
  );
  icons.alias = icons["icon-0"];
  const components = Object.fromEntries(
    componentNames.map((name) => [
      `porsche-design-system.${name}.abcdef.js`,
      name === "icon" ? JSON.stringify(icons) : `export const name = "${name}";`,
    ]),
  );
  return { indexPath, outputDir: join(root, "output"), coreName, core, components, icons };
}

test("sync downloads bounded concurrent assets and returns only after every byte is written", async (context) => {
  const input = await fixture(context);
  const requests = [];
  let active = 0;
  let maximum = 0;
  context.mock.method(console, "log", () => {});
  context.mock.method(globalThis, "fetch", async (url) => {
    requests.push(url);
    active += 1;
    maximum = Math.max(maximum, active);
    await setImmediate();
    active -= 1;
    const filename = basename(url);
    if (filename === input.coreName) return new Response(input.core);
    if (url.includes("/components/")) return new Response(input.components[filename]);
    if (url.includes("/icons/")) return new Response(`<svg>${filename}</svg>`);
    return new Response(new Uint8Array([0, 255, 128, 42]));
  });

  await syncPdsAssets(input);

  assert.equal(maximum, 8);
  assert.equal(active, 0);
  assert.equal(new Set(requests).size, requests.length);
  const components = await readdir(join(input.outputDir, "components"));
  assert.equal(components.length, Object.keys(input.components).length + 1);
  for (const [filename, content] of Object.entries({ ...input.components, [input.coreName]: input.core })) {
    assert.equal(await readFile(join(input.outputDir, "components", filename), "utf8"), content);
  }
  assert.deepEqual(
    (await readdir(join(input.outputDir, "icons"))).sort(),
    [...new Set(Object.values(input.icons))].sort(),
  );
  for (const filename of new Set(Object.values(input.icons))) {
    assert.equal(await readFile(join(input.outputDir, "icons", filename), "utf8"), `<svg>${filename}</svg>`);
  }
  const crests = await readdir(join(input.outputDir, "crest"));
  assert.equal(crests.length, 6);
  for (const filename of crests) {
    assert.deepEqual(await readFile(join(input.outputDir, "crest", filename)), Buffer.from([0, 255, 128, 42]));
  }
  assert.equal(console.log.mock.callCount(), 1);
});

test("sync stops scheduling on failure and joins in-flight bodies before rejecting", async (context) => {
  const input = await fixture(context);
  const started = Promise.withResolvers();
  const pending = [];
  let active = 0;
  let settled = false;
  context.mock.method(console, "log", () => {});
  context.mock.method(globalThis, "fetch", async (url) => {
    if (basename(url) === input.coreName) return new Response(input.core);
    assert.ok(url.includes("/components/"));
    const body = Promise.withResolvers();
    pending.push(body);
    active += 1;
    if (pending.length === 8) started.resolve();
    return {
      ok: true,
      text: async () => {
        try {
          return await body.promise;
        } finally {
          active -= 1;
        }
      },
    };
  });
  const error = new Error("connection lost while reading body");
  const result = syncPdsAssets(input).then(
    () => {
      settled = true;
      return null;
    },
    (failure) => {
      settled = true;
      return failure;
    },
  );
  try {
    await started.promise;
    pending[0].reject(error);
    await setImmediate();
    assert.equal(settled, false);
    assert.equal(active, 7);
  } finally {
    for (const body of pending) body.resolve("partial component");
    await result;
  }
  assert.equal(await result, error);
  assert.equal(active, 0);
  assert.equal(pending.length, 8);
  assert.equal(console.log.mock.callCount(), 0);
  assert.deepEqual(await readdir(join(input.outputDir, "icons")), []);
  assert.deepEqual(await readdir(join(input.outputDir, "crest")), []);
});

test("sync reports a failed HTTP request without announcing success", async (context) => {
  const input = await fixture(context);
  context.mock.method(console, "log", () => {});
  context.mock.method(globalThis, "fetch", async () => new Response("unavailable", { status: 503 }));

  await assert.rejects(syncPdsAssets(input), /cdn download failed.*HTTP 503/);

  assert.equal(console.log.mock.callCount(), 0);
});
