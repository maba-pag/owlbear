import { COLUMN, agentName } from "/assets/page/config/names.mjs";

// A step its own session time limit stopped (*r.rerun* from the host): which role timed out, each such role's limit as
// it is set now (never the value it had at the stop) and the step that runs again, in the Settings page's words.
function step(x) {
  return `the ${x.step} step${x.task ? ` of task ${x.task}${x.title ? ` (${x.title})` : ""}` : ""}`;
}

function limits(x) {
  return x.limits.map((l) => `${agentName(l.role)} ${l.minutes == null ? "not set now" : `now ${l.minutes} minutes`}`)
    .join("; ");
}

export function rerunWords(x) {
  return [`The session time limit of the ${agentName(x.role)} ended ${step(x)}.`,
    x.repairer ? `Then the time limit of the ${agentName("repairer")} ended Delivery's repair.` : "",
    `${COLUMN.minutes}: ${limits(x)}.`, `Run the step again runs ${step(x)} once more.`].filter(Boolean).join(" ");
}

// The confirmation of Run the step again (TD-151): what runs now, what Delivery then does, and the way out.
export function rerunAsk(x, paused) {
  return {
    title: `Run ${step(x)} again?`, yes: "Run the step again", no: "Keep it stopped",
    now: `Delivery runs ${step(x)} once more with the current settings (${COLUMN.minutes}: ${limits(x)}). Its work `
      + "so far, its open gates and the count of its timeouts stay.",
    then: `Delivery starts it on its next pass${paused ? ", once you resume this Change" : ""} and goes on as usual. `
      + "It uses more AI credits and may time out again: a repeated timeout is repaired as usual, and if that repair "
      + "fails the Change stops again.",
    after: "You can pause afterwards: that takes effect once the running step ends and doesn't undo what it did.",
    instead: "The Change stays stopped. You can pause or abandon it instead.",
  };
}
