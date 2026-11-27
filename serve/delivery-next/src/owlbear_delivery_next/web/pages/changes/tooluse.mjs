import { call } from "/assets/ui.mjs";
import { show, parts } from "./state.mjs";
import { notice } from "./widgets.mjs";
import { toolLines } from "./progress.mjs";

// The selected Change's tool calls, read apart from its detail: the host derives them from the whole spend ledger,
// again after every line a run adds, and no refresh of rows and detail waits for that. One answer or error is kept,
// for the selected Change; each refresh asks again (due) unless a read for that Change is still unanswered.
const WAIT = 60000;  // ms: the host goes on deriving after a page gives up, so asking again early only queues more
const asked = new Set();  // the keys whose read has no answer yet
let slot = null;  // { key, use, error, due }

export function due() {
  if (slot) slot.due = true;
}

function ask(d) {
  const key = d.key, [of, slug] = parts(key);
  slot.due = false;
  asked.add(key);
  call(`/changes/${encodeURIComponent(slug)}/tool-use`, { of, timeout: WAIT })
    .then((got) => [got.tool_use, ""], (error) => [null, error.message])
    .then(([use, error]) => {
      asked.delete(key);
      if (slot?.key !== key) return;  // another Change was selected meanwhile: its own read answers for it
      slot.error = error;
      if (!error) slot.use = use;
      show();
    });
}

// The detail's tool-call lines, shown with its details only; their place says in full why they could not be read.
export function toolUse(d) {
  if (slot?.key !== d.key) slot = { key: d.key, use: null, error: "", due: true };
  if (slot.due && !asked.has(d.key) && !d.old) ask(d);
  return slot.error ? notice("error", "Tool calls could not be read", slot.error) : toolLines(slot.use);
}
