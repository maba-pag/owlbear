import { call } from "/assets/ui.mjs";
import { INHERIT, LAYERS, NUMBERS, WRITE, state, drafts, page, show, showIdle, notify } from "./state.mjs";
import { mismatch, tierMismatch } from "./cells.mjs";
import { readAcross } from "./machine.mjs";
import { named } from "./sections.mjs";

function saved(layer, key) {
  const loaded = state.loaded;
  if (key === "widths") return (loaded[layer]?.widths ?? []).join(", ");
  if (["design_failures", "sessions", "curator_threshold"].includes(key)) return String(loaded[layer]?.[key] ?? "");
  if (key === "pr_labels" || key === "pr_marker" || key === "watcher") {
    const v = loaded[layer]?.[key];
    if (v === null || v === undefined) return "";
    return key === "pr_labels" ? v.join(", ") || "none" : v ? "on" : "off";
  }
  const [role, field] = key.split(".");
  const value = role === "final_review" ? loaded[layer]?.final_review?.[field]
    : role === "machine" ? loaded[layer]?.machine?.[field] : loaded[layer]?.agents?.[role]?.[field];
  return value === null || value === undefined ? "" : String(value);
}

// The edited layer's value of *key*: the draft as typed, else the saved value.
export function own(key) {
  return key in drafts[state.layer] ? drafts[state.layer][key] : saved(state.layer, key);
}

export function inherited() {
  return state.loaded.inherited[state.layer];
}

// One edit of the edited layer; a value equal to the saved one is no edit, an inherit choice clears the value.
// A *literal* value is typed text, where "inherit" is just a word (a label may be named so).
export function edit(key, raw, literal = false) {
  const field = key.split(".")[1] ?? key;
  const value = !literal && !NUMBERS.includes(field) && raw === INHERIT ? "" : raw;
  if (value.trim() === saved(state.layer, key)) delete drafts[state.layer][key];
  else drafts[state.layer][key] = value;
  show();
}

// The edited layer's drafts that differ from what is saved, trimmed as they will be sent.
function dirty(layer) {
  return Object.entries(drafts[layer]).filter(([key, value]) => value.trim() !== saved(layer, key));
}

// Each unsaved edit of *layer* as "field: saved → new"; a blank value inherits.
function changes(layer) {
  const said = (v) => (v === "" || v === null || v === undefined ? "inherited" : v);
  return dirty(layer).map(([key, value]) =>
    `${key.replace(".", " ").replaceAll("_", " ")}: ${said(saved(layer, key))} → ${said(value.trim())}`);
}

export function pendingLine() {
  const others = Object.keys(drafts).filter((l) => l !== state.layer && dirty(l).length);
  const mine = changes(state.layer), parts = mine.length ? [`Unsaved: ${mine.join("; ")}.`] : ["No unsaved edits."];
  for (const other of others) parts.push(`${LAYERS[other]}: ${dirty(other).length} more unsaved.`);
  return parts.join(" ");
}

function edited(layer) {
  const next = structuredClone(state.loaded[layer]);
  for (const [key, raw] of dirty(layer)) {
    const value = raw.trim();
    if (key === "widths") {
      next.widths = value ? value.split(",").map((w) => Number(w.trim())) : null;
      continue;
    }
    if (key === "design_failures") {
      next[key] = value || null;
      continue;
    }
    if (key === "sessions" || key === "curator_threshold") {
      next[key] = value === "" ? null : /^\d+$/.test(value) ? Number(value) : value;
      continue;
    }
    if (key === "pr_labels") {
      next[key] = !value ? null : value === "none" ? [] : value.split(",").map((l) => l.trim()).filter(Boolean);
      continue;
    }
    if (key === "pr_marker" || key === "watcher") {
      next[key] = value ? value === "on" : null;
      continue;
    }
    const [role, field] = key.split(".");
    const number = !NUMBERS.includes(field) || value === "" ? null : /^\d+$/.test(value) ? Number(value) : value;
    if (role === "machine") {  // Global's machine settings (2026-10-23): "true"/"false" for the switches
      const flag = value === "" ? null : value === "true";
      const mine = { ...(next.machine ?? {}), [field]: field.startsWith("update_") ? flag : number ?? (value || null) };
      next.machine = Object.values(mine).some((v) => v !== null) ? mine : null;
      continue;
    }
    if (role === "final_review") {
      const mine = { ...(next.final_review ?? {}), [field]: number };
      next.final_review = Object.values(mine).some((v) => v !== null) ? mine : null;
      continue;
    }
    const agent = next.agents[role] ?? {};
    agent[field] = field === "subagents" ? (value ? value === "true" : null) : number ?? (value || null);
    if (Object.values(agent).some((v) => v !== null)) next.agents[role] = agent;
    else delete next.agents[role];
  }
  return next;
}

export async function reload() {
  try {
    state.loaded = await call("/config");
    state.error = state.loaded.notice ? state.loaded.notice.charAt(0).toUpperCase() + state.loaded.notice.slice(1) : "";
    return true;
  } catch (e) {
    notify(e.message);
    return false;
  }
}

export async function save() {
  if (state.saving || !state.loaded) return;
  const roles = Object.keys(state.loaded.settings.agents);
  const wrong = roles.flatMap((r) => [mismatch(r), tierMismatch(r)]).filter(Boolean);
  if (wrong.length) return notify(`Not saved: ${wrong.join("; ")}.`);
  const layer = state.layer, sent = { ...drafts[layer] };
  if (layer === "global" && !(await ask({
    title: "Change the defaults for all projects?", yes: "Save global defaults", no: "Keep editing",
    now: "These become the defaults for every project:", items: changes(layer),
    then: "Each project's next session uses them, unless this machine or the project sets its own value; sessions "
      + "running now keep theirs.",
    after: "Change them back here at any time.",
    instead: "Your edits stay unsaved on this page.",
  }))) return;
  if (layer === "machine" && !(await ask({
    title: "Change this machine's preferences?", yes: "Save this machine's preferences", no: "Keep editing",
    now: "These apply to every project on this machine:", items: changes(layer),
    then: "Each project's next session here uses them, unless the project sets its own value; other machines and "
      + "sessions running now keep theirs.",
    after: "Change them back here at any time.",
    instead: "Your edits stay unsaved on this page.",
  }))) return;
  const project = named() || "this project";
  if (layer === "project" && !(await ask({
    title: `Change ${project}'s settings?`, yes: "Save project settings", no: "Keep editing",
    now: `These apply to ${project} only, on every machine:`, items: changes(layer),
    then: "Its next session uses them; sessions running now keep theirs.",
    after: "Change them back here at any time.",
    instead: "Your edits stay unsaved on this page.",
  }))) return;
  state.saving = true;
  state.status = "Saving…";
  show();
  try {
    state.loaded = await call(`/config/${layer}`,
      { method: "PUT", body: { rev: state.loaded[`${layer}_rev`], layer: edited(layer) }, timeout: WRITE });
    for (const [key, value] of Object.entries(sent)) if (drafts[layer][key] === value) delete drafts[layer][key];
    state.error = state.loaded.notice ? state.loaded.notice.charAt(0).toUpperCase() + state.loaded.notice.slice(1) : "";
    const whose = { global: "the global", machine: "this machine's" }[layer]
      ?? (named() ? `${named()}'s` : "this project's");
    state.status = `Saved ${whose} settings. They apply to the next session.`;
    await readAcross();
  } catch (e) {
    state.status = "";
    if (e.status === 409 && await reload()) {
      await readAcross();
      state.error = `${e.message}. The page loaded the current settings and kept your unsaved edits; `
        + "check them and save again.";
      state.error = state.error.charAt(0).toUpperCase() + state.error.slice(1);
    } else {
      state.error = e.message.charAt(0).toUpperCase() + e.message.slice(1);
    }
  } finally {
    state.saving = false;
    showIdle();  // models that arrived during it apply now
  }
}

export async function rename() {
  const loaded = state.loaded, name = (state.folder ?? loaded?.folder ?? "").trim();
  if (state.saving || !loaded?.folder || !name || name === loaded.folder) return;
  const sure = await ask({
    title: `Rename the folder ${loaded.folder} to ${name}?`, yes: "Rename", no: "Keep the name",
    now: "Delivery moves the folder with this project's settings, memory and visual decisions in the shared "
      + "settings repository, then commits and pushes the move. It refuses while a step of this project runs.",
    then: "Other clones of this project use the new name the next time they start.",
    after: "Rename it again here at any time; your source checkout keeps its name.",
    instead: "The folder keeps its name.",
  });
  if (!sure) return;
  state.saving = true;
  state.status = "Renaming…";
  show();
  try {
    state.loaded = await call("/config/folder", { method: "PUT", body: { name }, timeout: WRITE });
    state.folder = null;
    state.error = state.loaded.notice ? state.loaded.notice.charAt(0).toUpperCase() + state.loaded.notice.slice(1) : "";
    state.status = `This project's folder is now ${state.loaded.folder}.`;
  } catch (e) {
    state.status = "";
    state.error = e.message.charAt(0).toUpperCase() + e.message.slice(1);
  } finally {
    state.saving = false;
    showIdle();  // models that arrived during it apply now
  }
}

// The offered models replace typing once read; the runtime starts for it, so this can take a while.
export async function readModels() {
  state.modelsNote = "Reading the models this machine's Copilot offers…";
  show();
  try {
    const answer = await call("/config/models", { timeout: 45000 });
    const offered = answer.models.length ? answer.models : null;
    const note = offered ? "Models, efforts and context sizes as this machine's Copilot offers them."
      : `Could not read the offered models (${answer.error || "none offered"}); type a model name.`;
    page.arrived = { offered, note };
  } catch (e) {
    page.arrived = { offered: null, note: `Could not read the offered models (${e.message}); type a model name.` };
  }
  showIdle();
}
