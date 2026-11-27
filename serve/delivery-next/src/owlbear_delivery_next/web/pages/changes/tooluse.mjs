import { call } from "/assets/ui.mjs";
import { show } from "./state.mjs";
import { notice, text } from "./widgets.mjs";
import { toolLines } from "./progress.mjs";

// The selected Change's tool calls, read apart from its detail: the host derives them from the whole spend ledger,
// again after every line a run adds, and no refresh of rows and detail waits for that. Each detail the page reads
// asks once, unless a read for that Change is still unanswered; the last answer, or the last read's error, is kept
// for the selected Change. A read may take 60 s: the host goes on deriving after a page gives up, so asking again
// early only queues more.
const read = new WeakSet();  // the details that asked
const asked = new Set();  // the keys whose read has no answer yet
let slot = null;  // { key, got }: got is the answer, an Error, or null before the first

function ask(d) {
  const key = d.key;
  read.add(d);
  asked.add(key);
  call(`/changes/${encodeURIComponent(d.slug)}/tool-use`, { of: d.project, timeout: 60000 })
    .then((got) => got.tool_use, (error) => error)
    .then((got) => {
      asked.delete(key);
      if (slot?.key !== key) return;  // another Change was selected meanwhile: its own read answers for it
      slot.got = got;
      show();
    });
}

// The detail's tool-call lines, shown with its details only; their place says in full why they could not be read.
export function toolUse(d) {
  if (slot?.key !== d.key) slot = { key: d.key, got: null };
  if (!read.has(d) && !asked.has(d.key) && !d.old) ask(d);
  if (slot.got instanceof Error) return notice("error", "Tool calls could not be read", slot.got.message);
  return slot.got ? toolLines(slot.got) : text("Reading the tool calls", { size: "xs", color: "contrast-medium" });
}
