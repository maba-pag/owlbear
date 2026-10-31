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

function shape(of) {
  return openChat({
    path: "/new-change", of, opened: "A chat opened in VS Code to shape the new Change.",
    dialog: {
      title: "Shape a new Change?", yes: "Open the chat", no: "Not now",
      now: "A chat opens in VS Code where the shaper works out the brief with you; the chat uses AI credits like any "
        + "Copilot chat.",
      then: "Nothing is built. When you save the brief in the chat, it appears here for your approval.",
      after: "Approve it here to start the work, or keep shaping it in the chat.",
      instead: "Nothing opens.",
    },
  });
}

// A saved brief opens a new shaping chat in its Change's project; the Change stays as it is until the chat saves.
export function reviseBrief(d) {
  const v = d.brief.version;
  return openChat({
    path: `/changes/${encodeURIComponent(d.slug)}/revise-brief`, of: d.project,
    opened: `A chat opened in VS Code to revise ${d.handle}.`,
    dialog: {
      title: `Revise brief v${v} in a new chat?`, yes: "Open the chat", no: "Not now",
      now: `A chat opens in VS Code where the shaper revises brief v${v} of ${d.handle} with you; the chat uses AI `
        + "credits like any Copilot chat.",
      then: "Nothing is built, and the brief here stays as it is. When the shaper saves the revision, it appears "
        + "here as a new version for your approval.",
      after: "Approve the new version here, or keep shaping it in the chat.",
      instead: "Nothing opens; the brief stays as it is.",
    },
  });
}

// Asks first, then opens the shaping chat through *path* and says how it went (TD-83).
async function openChat({ path, of, dialog, opened }) {
  if (!(await ask(dialog))) return;
  state.creating = true;
  state.started = { text: "Opening the shaping chat…" };
  show();
  try {
    const r = await call(path, {}, of);
    const s = r.started ? await launched(r.launch, of) : { state: "failed", ...r };
    state.started = s.state === "open"
      ? { text: `${opened}${s.warning ? ` Note: ${s.warning}.` : ""}` }
      : { reason: s.reason, command: s.command };
  } catch (e) {
    state.started = null;
    failed(e);
  } finally {
    state.creating = false;
    show();
  }
}
