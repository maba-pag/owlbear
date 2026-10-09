import { spawn } from "node:child_process";
import { once } from "node:events";
import { mkdir, mkdtemp, rm, utimes, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const root = resolve(import.meta.dirname, "../../../../..");
const fixture = await mkdtemp(join(tmpdir(), "owlbear-work-portfolio-"));
// Stuck-worker Changes live in their own workspace so the portfolio fixture's counts stay unchanged.
const stuckFixture = await mkdtemp(join(tmpdir(), "owlbear-work-stuck-worker-"));
// Merge-approval Changes talk to a fake `gh`; the spec drives fake GitHub through this fixed root.
const mergeRoot = join(tmpdir(), "owlbear-work-merge-4177");
await rm(mergeRoot, { recursive: true, force: true });
const mergeFixture = join(mergeRoot, "workspace");
const fakeGhBin = join(mergeRoot, "bin");
const fakeGhState = join(mergeRoot, "fake-gh.json");
await mkdir(mergeFixture, { recursive: true });
await mkdir(fakeGhBin, { recursive: true });
await writeFile(
  join(fakeGhBin, "gh"),
  `#!/bin/sh\nexec "${process.execPath}" "${resolve(import.meta.dirname, "fake-gh.mjs")}" "$@"\n`,
  { mode: 0o755 },
);
const fakeGhEnv = { PATH: `${fakeGhBin}:${process.env.PATH}`, OWLBEAR_FAKE_GH_STATE: fakeGhState };
const fixtures = [fixture, stuckFixture, mergeRoot];
const servers = [];
let activeWorker;

// Playwright stops its webServer with SIGKILL, so a detached reaper removes the fixtures once this process is gone.
spawn(
  process.execPath,
  [
    "-e",
    `const [pid, ...paths] = process.argv.slice(1);
const timer = setInterval(() => {
  try { process.kill(Number(pid), 0); } catch {
    clearInterval(timer);
    for (const path of paths) require("node:fs").rmSync(path, { recursive: true, force: true });
  }
}, 500);`,
    String(process.pid),
    ...fixtures,
  ],
  { detached: true, stdio: "ignore" },
).unref();

async function run(command, arguments_, env = {}) {
  const process_ = spawn(command, arguments_, { cwd: root, env: { ...process.env, ...env }, stdio: "inherit" });
  const [exitCode] = await once(process_, "exit");
  if (exitCode !== 0) throw new Error(`${command} exited with ${exitCode ?? "no status"}`);
}

async function seed(workspace, options = [], env = {}) {
  await run(
    "uv",
    [
      "run",
      "--project",
      root,
      "python",
      resolve(import.meta.dirname, "seed-work-portfolio-delivery.py"),
      "--workspace",
      workspace,
      ...options,
    ],
    env,
  );
}

function startCockpit(workspace, port, env = {}) {
  const server = spawn("uv", ["run", "--project", root, "--package", "owlbear-cockpit", "cockpit"], {
    cwd: workspace,
    env: {
      ...process.env,
      ...env,
      COCKPIT_PORT: port,
      COCKPIT_NO_OPEN: "1",
    },
    stdio: "inherit",
  });
  servers.push(server);
  server.on("exit", async (code) => {
    await cleanup();
    process.exit(code ?? 1);
  });
  return server;
}

async function waitForLive(port) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    try {
      if ((await fetch(`http://127.0.0.1:${port}/health/live`)).ok) return;
    } catch {
      // The server is still starting.
    }
    await delay(500);
  }
  throw new Error(`Cockpit on port ${port} did not become live`);
}

let cleaning;
function cleanup() {
  cleaning ??= (async () => {
    clearInterval(activeWorker);
    for (const server of servers) {
      if (!server.killed) server.kill("SIGTERM");
    }
    await Promise.all(fixtures.map((path) => rm(path, { recursive: true, force: true })));
  })();
  return cleaning;
}

try {
  await seed(fixture);
  await seed(stuckFixture, ["--stuck-workers"]);
  await seed(mergeFixture, ["--merges", fakeGhState], fakeGhEnv);
} catch (error) {
  await cleanup();
  throw error;
}

process.on("SIGTERM", cleanup);
process.on("SIGINT", cleanup);

// A worker that is still running keeps writing to its worktree inside the 30-second write guard.
const activeFile = join(stuckFixture, ".owlbear/delivery/worktrees/stuck-active-e2e/product.txt");
activeWorker = setInterval(() => {
  const now = new Date();
  utimes(activeFile, now, now).catch(() => {});
}, 10_000);

// A leftover worker process keeps its working directory in the busy worktree; it exits with this stack.
const busyWorker = spawn(
  process.execPath,
  [
    "-e",
    `const pid = Number(process.argv[1]);
setInterval(() => { try { process.kill(pid, 0); } catch { process.exit(0); } }, 500);`,
    String(process.pid),
  ],
  { cwd: join(stuckFixture, ".owlbear/delivery/worktrees/stuck-busy-e2e"), detached: true, stdio: "ignore" },
);
busyWorker.unref();
servers.push(busyWorker);

startCockpit(stuckFixture, "4176");
startCockpit(mergeFixture, "4177", fakeGhEnv);
try {
  await waitForLive("4176");
  await waitForLive("4177");
} catch (error) {
  await cleanup();
  throw error;
}
startCockpit(fixture, "4175");
