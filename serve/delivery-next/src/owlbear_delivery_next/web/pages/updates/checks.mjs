// What the machine's update checks found (D-01M63CCVRK8ZKFENY9F4A2K11A), read once per page for the menu's marker and
// the Updates pages' frame. A clone's own host has no checks: nothing is read there.
import { call, machineState } from "/assets/ui.mjs";

const AGAIN = 1500;  // how often it reads while a check runs, until its result is in
export const checks = { all: null, unread: "" };
const listeners = new Set();
let reading = 0, again = null;

// *show* runs whenever what was read changes.
export function listen(show) {
  listeners.add(show);
}

// The update named *name* as last read, or undefined.
export function update(name) {
  return checks.all?.updates.find((u) => u.name === name);
}

function took(got, n) {
  if (n !== reading) return;  // a later read is under way; it shows the newer state
  checks.all = got;
  checks.unread = "";
  for (const show of listeners) show();
  clearTimeout(again);
  if (got.updates.some((u) => u.checking)) again = setTimeout(readChecks, AGAIN);
}

export async function readChecks() {
  if (!machineState()) return;
  const n = ++reading;
  try {
    took(await call("/updates", { machine: true }), n);
  } catch (e) {
    if (n !== reading) return;
    checks.unread = e.message;
    for (const show of listeners) show();
  }
}

// Search for updates: the check runs in the background; its result is read until it is in.
export async function search(name) {
  took(await call(`/updates/${name}/check`, { method: "POST", machine: true, timeout: 10000 }), ++reading);
}

document.addEventListener("owlbear-polled", () => readChecks());
readChecks();
