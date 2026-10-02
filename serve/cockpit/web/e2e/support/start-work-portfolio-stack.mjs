import { spawn } from "node:child_process";
import { once } from "node:events";
import { mkdtemp, rm, utimes } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { setTimeout as delay } from "node:timers/promises";

const root = resolve(import.meta.dirname, "../../../../..");
const fixture = await mkdtemp(join(tmpdir(), "owlbear-work-portfolio-"));
// Stuck-worker Changes live in their own workspace so the portfolio fixture's counts stay unchanged.
const stuckFixture = await mkdtemp(join(tmpdir(), "owlbear-work-stuck-worker-"));
const fixtures = [fixture, stuckFixture];
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

async function run(command, arguments_) {
  const process = spawn(command, arguments_, { cwd: root, stdio: "inherit" });
  const [exitCode] = await once(process, "exit");
  if (exitCode !== 0) throw new Error(`${command} exited with ${exitCode ?? "no status"}`);
}

async function seed(workspace, ...options) {
  await run("uv", [
    "run",
    "--project",
    root,
    "python",
    resolve(import.meta.dirname, "seed-work-portfolio-delivery.py"),
    "--workspace",
    workspace,
    ...options,
  ]);
}

function startCockpit(workspace, port) {
  const server = spawn("uv", ["run", "--project", root, "--package", "owlbear-cockpit", "cockpit"], {
    cwd: workspace,
    env: {
      ...process.env,
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
  await seed(stuckFixture, "--stuck-workers");
} catch (error) {
  await cleanup();
  throw error;
}

process.on("SIGTERM", cleanup);
process.on("SIGINT", cleanup);

// A worker that is still running keeps writing to its worktree.
const activeFile = join(stuckFixture, ".owlbear/delivery/worktrees/stuck-active-e2e/product.txt");
activeWorker = setInterval(() => {
  const now = new Date();
  utimes(activeFile, now, now).catch(() => {});
}, 10_000);

startCockpit(stuckFixture, "4176");
try {
  await waitForLive("4176");
} catch (error) {
  await cleanup();
  throw error;
}
startCockpit(fixture, "4175");
