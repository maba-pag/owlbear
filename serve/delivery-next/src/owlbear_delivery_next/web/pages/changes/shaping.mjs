import { html } from "/assets/lit-html/3.3.3/lit-html.js";
import { project, shown } from "/assets/ui.mjs";
import { state, show, call, several, failed } from "./state.mjs";
import { button } from "./widgets.mjs";

export function startedView() {
  if (state.choosing) return chooserView();
  const s = state.started;
  if (!s) return html`<p-text id="started" aria-live="polite"></p-text>`;
  return html`<p-text id="started" aria-live="polite">${s.text ?? html`Could not open the chat: ${s.reason}. Copy
    this command: <code>${s.command}</code>`}</p-text>`;
}

async function launched(id, of) {  // the host opens the chat in the background; VS Code may first have to start
  for (;;) {
    const s = await call(`/new-change/${encodeURIComponent(id)}`, undefined, of);
    if (s.state !== "opening") return s;
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}

// New Change asks which project first when the page shows several (TD-241).
export function newChange() {
  if (several()) {
    state.choosing = shown()[0].id;
    show();
    document.querySelector("#choose p-select")?.focus();
    return undefined;
  }
  return shape(shown()?.[0]?.id ?? project);
}

function chooserView() {
  const picked = (e) => { state.choosing = e.target.value; };
  const go = () => {
    const of = state.choosing;
    state.choosing = false;
    show();  // the chooser goes at once, whatever the confirmation then says
    shape(of);
  };
  const stop = () => { state.choosing = false; show(); };
  return html`<div id="choose" class="row"><p-select label="Shape the new Change in" .value=${state.choosing}
    @change=${picked}>${shown().map((p) => html`<p-select-option value=${p.id}>${p.name}</p-select-option>`)}
    </p-select>
    ${button("Continue", go)}${button("Cancel", stop, { variant: "secondary" })}</div>`;
}

async function shape(of) {
  const wanted = await ask({
    title: "Shape a new Change?", yes: "Open the chat", no: "Not now",
    now: "A chat opens in VS Code where the shaper works out the brief with you; the chat uses AI credits like any "
      + "Copilot chat.",
    then: "Nothing is built. When you save the brief in the chat, it appears here for your approval.",
    after: "Approve it here to start the work, or keep shaping it in the chat.",
    instead: "Nothing opens.",
  });
  if (!wanted) return;
  state.creating = true;
  state.started = { text: "Opening the shaping chat…" };
  show();
  try {
    const r = await call("/new-change", {}, of);
    const s = r.started ? await launched(r.launch, of) : { state: "failed", ...r };
    state.started = s.state === "open"
      ? { text: `A chat opened in VS Code to shape the new Change.${s.warning ? ` Note: ${s.warning}.` : ""}` }
      : { reason: s.reason, command: s.command };
  } catch (e) {
    state.started = null;
    failed(e);
  } finally {
    state.creating = false;
    show();
  }
}
