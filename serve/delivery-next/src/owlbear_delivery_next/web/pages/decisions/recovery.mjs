import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { call } from "/assets/ui.mjs";
import { refresh } from "./list.mjs";
import { show, state, WRITE } from "./state.mjs";
import { button } from "./widgets.mjs";

// The owner's own recovery of an interrupted decision batch. It reads the journal directly, so it stays reachable
// while the decision list is blocked, and it names the batch generation the owner saw; a stale answer is refused.
const DONE = { finish: "Finished", abandon: "Abandoned" };
const EFFECT = {
  finish: "It publishes the decisions and conflict flags the batch wrote, then retires the batch.",
  abandon: "It restores the decision files to their state before the batch, then retires the batch.",
};
const TITLE = { finish: "Finish", abandon: "Abandon" };

export async function loadRecovery() {
  try {
    state.recovery.status = await call("/decisions/recovery");
    state.recovery.error = "";
  } catch (error) {
    state.recovery.status = null;
    state.recovery.error = error.message;
  }
}

async function decide(action) {
  const status = state.recovery.status;
  if (!status?.interrupted || status.corrupt || state.recovery.pending) return;
  const generation = status.generation, verb = TITLE[action];
  const yes = await ask({ title: `${verb} the interrupted decision batch?`, yes: verb,
    now: `${EFFECT[action]} Batch ${generation} for project ${status.project}; ${status.ids.length} decision(s).`,
    then: "Nothing in Git or the index is undone.",
    after: "Decisions are read and changed normally again.",
    instead: "The batch stays interrupted and decisions stay blocked." });
  if (!yes) return;
  state.recovery.pending = action;
  state.recovery.notice = "";
  show();
  let notice = "", failure = "";
  try {
    const r = await call(`/decisions/recovery/${action}`, { body: { generation, confirmed: true }, timeout: WRITE });
    notice = r.done ? `${DONE[action]} batch ${generation}. ${r.notice}`.trim() : `Not ${action}ed: ${r.notice}`;
  } catch (error) {
    failure = error.message;
  }
  state.recovery.pending = "";
  state.recovery.notice = notice;
  await refresh();
  if (failure) {
    state.recovery.error = failure;
    show();
  }
}

function facts(status) {
  return html`<section id="recovery-batch" aria-label="The interrupted batch">
    <p-text size="sm">Project: <span class="recovery-project">${status.project}</span></p-text>
    <p-text size="sm">Generation: <span class="recovery-generation">${status.generation}</span></p-text>
    <p-text size="sm">Decisions: <span class="recovery-ids">${status.ids.join(", ")}</span></p-text>
    <p-text size="sm">Message: ${status.message}</p-text>
    <p-text size="sm">Head: ${status.head}</p-text>
  </section>`;
}

export function recoveryView() {
  const { status, error, notice, pending } = state.recovery;
  const failed = error ? html`<p-inline-notification id="recovery-error" state="error" dismiss-button="false">
    ${error}</p-inline-notification>` : nothing;
  const result = notice ? html`<p-text id="recovery-notice" role="status">${notice}</p-text>` : nothing;
  if (!status) return html`${failed}${result}`;
  if (status.corrupt) {
    return html`<section id="recovery" aria-label="Decision journal">
      <p-inline-notification id="recovery-corrupt" state="error" heading="The decision journal cannot be read"
        heading-tag="h2" dismiss-button="false">${status.diagnosis}</p-inline-notification>
      <p-text size="sm">Finish and Abandon are disabled until the journal can be read.
        Nothing is cleared automatically.</p-text>
      ${failed}${result}
    </section>`;
  }
  if (!status.interrupted) return html`${failed}${result}`;
  return html`<section id="recovery" aria-label="Interrupted decision batch">
    <p-inline-notification id="recovery-interrupted" state="warning" heading="A decision batch was interrupted"
      heading-tag="h2" dismiss-button="false">Decisions stay blocked until you finish or abandon this batch.
    </p-inline-notification>
    ${facts(status)}
    <p-text size="sm">Finish publishes the batch as it was written. Abandon restores the decision files from before it.
      Neither undoes anything in Git or the index.</p-text>
    <div class="row">
      ${button("Finish batch", () => decide("finish"), { variant: "primary", busy: pending === "finish" })}
      ${button("Abandon batch", () => decide("abandon"), { variant: "secondary", busy: pending === "abandon" })}
    </div>
    ${failed}${result}
  </section>`;
}
