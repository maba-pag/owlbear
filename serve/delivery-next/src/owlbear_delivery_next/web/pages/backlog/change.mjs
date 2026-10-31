import { html } from "/assets/lit-html/3.3.3/lit-html.js";
import { blockedOf, call } from "/assets/ui.mjs";
import { GET, WRITE, state, show, notify } from "./state.mjs";
import { button, select } from "./widgets.mjs";
import { clonesOf } from "./entries.mjs";
import { chosen, refresh } from "./view.mjs";

async function launched(id, of) {  // the host opens the chat in the background; VS Code may first have to start
  for (;;) {
    const s = await call(`/new-change/${encodeURIComponent(id)}`, { timeout: GET, of });
    if (s.state !== "opening") return s;
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}

// The clones of entry *e*'s repository a Change may start in: those whose settings let work start (#808).
function startable(e) {
  return clonesOf(e).filter((c) => !blockedOf(c.id));
}

// The clone a Change from *picked* starts in, when the entries name it: one project, held by one clone here. A
// Global or untriaged entry names none.
function clear(picked) {
  const clones = clonesOf(picked[0]), named = new Set(picked.flatMap((e) => (e.projects?.length ? e.projects : ["?"])));
  const only = named.size === 1 && !named.has("?") ? clones.filter((c) => c.name === [...named][0]) : [];
  return clones.length === 1 ? clones[0] : only.length === 1 ? only[0] : null;
}

// Why no Change can start from *picked*, or "" (#808): the clone they name may not start work, or no clone the owner
// could choose may.
export function held(picked) {
  if (!picked.length) return "";
  const target = clear(picked);
  if (target) return blockedOf(target.id);
  return startable(picked[0]).length ? "" : "every project's settings are unset or can't be read";
}

// Global, untriaged or several projects' entries, or a project with several clones here: the owner picks the clone.
// The choice follows the machine's poll: a clone whose work stops being able to start is replaced or cleared.
export function chooser() {
  const clones = startable(state.choosing.picked[0]);
  if (!clones.some((c) => c.id === state.choosing.of)) state.choosing.of = clones[0]?.id ?? null;
  const go = () => { const { picked, of } = state.choosing; state.choosing = null; show(); shapeFrom(picked, of); };
  const stop = () => { state.choosing = null; show(); };
  const why = held(state.choosing.picked);
  return html`<div id="choose" class="row">${select("Shape the Change in", clones.map((c) => [c.id, c.label]),
    state.choosing.of ?? "", (v) => { state.choosing.of = v; show(); })}
    ${button("Continue", go, { disabled: state.choosing.of === null, title: why })}
    ${button("Cancel", stop, { variant: "secondary" })}</div>`;
}

export async function createChange() {
  const picked = chosen();
  if (!picked.length) return notify("Select one or more entries first.");
  if (new Set(picked.map((e) => e.repository)).size > 1) {
    return notify("These entries are in different repositories' backlogs; pick entries of one of them.");
  }
  const why = held(picked);
  if (why) return notify(why);
  const target = clear(picked);
  if (target) return shapeFrom(picked, target.id);
  state.choosing = { picked, of: startable(picked[0])[0].id };
  show();
  return undefined;
}

async function shapeFrom(picked, of) {
  const titles = picked.map((e) => e.title), many = picked.length > 1;
  const wanted = await ask({
    title: `Shape a Change from ${many ? `these ${picked.length} entries` : "this entry"}?`, yes: "Open the chat",
    no: "Keep selected",
    now: "A chat opens in VS Code where the shaper turns them, with their notes, evidence and links, into a brief; "
      + "the chat uses AI credits. Once it opens, they are marked as in a Change.",
    items: titles,
    then: "Nothing is built. The brief appears on the Changes page for your approval.",
    after: "Approve the brief there to start the work; set each entry's Change here once it exists.",
    instead: "The entries stay selected and unchanged.",
  });
  if (!wanted) return;
  state.creating = true;
  state.started = { text: "Opening the shaping chat…" };
  show();
  try {
    const r = await call("/backlog/change", { body: { ids: picked.map((e) => e.id) }, timeout: WRITE, of });
    const s = r.started ? await launched(r.launch, of) : { state: "failed", ...r };
    if (r.started) state.selected.clear();
    state.error = "";
    state.started = s.state === "open"
      ? { text: `A chat opened in VS Code to shape a Change from ${picked.length} entries.`
        + (s.warning ? ` Note: ${s.warning}.` : "") }
      : { reason: s.reason, command: s.command };
  } catch (e) {
    state.started = null;
    state.error = e.message.charAt(0).toUpperCase() + e.message.slice(1);
  } finally {
    state.creating = false;
    await refresh();
  }
}
