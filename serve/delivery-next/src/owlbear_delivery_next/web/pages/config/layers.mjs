import { call } from "/assets/ui.mjs";
import { CREDITS, INHERIT, LAYERS, NUMBERS, WRITE, state, drafts, page, show, showIdle, notify, typedNumber }
  from "./state.mjs";
import { USER_KEYS, mismatch, tierMismatch } from "./cells.mjs";
import { readAcross } from "./machine.mjs";
import { named } from "./sections.mjs";

function saved(layer, key) {
  const loaded = state.loaded;
  if (key.startsWith("prefs.")) {
    const v = loaded[layer]?.prefs?.[key.slice(6)];
    if (v === null || v === undefined) return "";
    return typeof v === "boolean" ? (v ? "on" : "off") : String(v);
  }
  if (key === "widths") return (loaded[layer]?.widths ?? []).join(", ");
  if (["design_failures", "sessions", "curator_threshold"].includes(key)) return String(loaded[layer]?.[key] ?? "");
  if (key.startsWith("spot.")) {  // the Spotter's settings (design §4)
    const v = loaded[layer]?.spotter?.[key.slice(5)];
    return v === null || v === undefined ? "" : Array.isArray(v) ? v.join(", ") : String(v);
  }
  if (key === "pr_labels" || key === "pr_marker" || USER_KEYS.includes(key)) {
    const v = loaded[layer]?.[key];
    if (v === null || v === undefined) return "";
    return key === "pr_labels" ? v.join(", ") || "none" : v ? "on" : "off";
  }
  const [role, field] = key.split(".");
  const value = role === "final_review" ? loaded[layer]?.final_review?.[field]
    : role === "machine" ? loaded[layer]?.machine?.[field] : loaded[layer]?.agents?.[role]?.[field];
  if (value === null || value === undefined) return "";
  return Array.isArray(value) ? value.join(", ") || "none" : String(value);
}

// A list's text as typed, shown only while its items are what the field holds now: an edit's, else the saved
// ones; display only, never an edit itself (so a reload or a conflict never turns old text into one).
const typing = { project: {}, machine: {}, global: {} };

// The edited layer's value of *key*: the draft as typed, else the saved value.
export function own(key) {
  const value = key in drafts[state.layer] ? drafts[state.layer][key] : saved(state.layer, key);
  const text = typing[state.layer][key];
  return text !== undefined && canonical(key, text) === canonical(key, value) ? text : value;
}

export function inherited() {
  return state.loaded.inherited[state.layer];
}

// One edit of the edited layer; a value equal to the saved one is no edit, an inherit choice clears the value.
// A *literal* value is typed text, where "inherit" is just a word (a label may be named so).
export function edit(key, raw, literal = false) {
  const field = key.split(".")[1] ?? key;
  // even a no-op clear is a review
if (state.layer === "project" && key.startsWith("prefs.")) state.prefsReview = true;
  const value = !literal && !NUMBERS.includes(field) && !CREDITS.includes(field) && raw === INHERIT ? "" : raw;
  if (LISTS.includes(key)) typing[state.layer][key] = value;  // shown as typed: a comma, a space
  if (canonical(key, value) === saved(state.layer, key)) delete drafts[state.layer][key];
  else drafts[state.layer][key] = value;
  show();
}

// The value a preference's text sends: blank clears it; the server checks the rest (no bounds are guessed here).
function prefValue(field, value) {
  if (value === "") return null;
  if (field === "delete_remote_branch" || field === "ask_before_merge") return value === "on";
  if (field.startsWith("ci_")) return /^\d+$/.test(value) ? Number(value) : value;
  return value;
}

// A list's text as it is saved: items trimmed, empty ones dropped, joined alike; other text trimmed.
const LISTS = ["spot.looks", "machine.enrolled_chats"];
function canonical(key, text) {
  const value = text.trim();
  if (!LISTS.includes(key) || value === "none") return value;
  return value.split(",").map((i) => i.trim()).filter(Boolean).join(", ");
}

// The edited layer's drafts that differ from what is saved, compared as they will be sent.
function dirty(layer) {
  return Object.entries(drafts[layer]).filter(([key, value]) => canonical(key, value) !== saved(layer, key));
}

// Each unsaved edit of *layer* as "field: saved → new"; a blank value inherits.
function changes(layer) {
  const said = (v) => (v === "" || v === null || v === undefined ? "inherited" : v);
  return dirty(layer).map(([key, value]) =>
    `${key.replace(".", " ").replaceAll("_", " ")}: ${said(saved(layer, key))} → ${said(value.trim())}`);
}

// Confirms a pending legacy import's Merge and cleanup preferences as reviewed, with no edit: the saved values stand.
// The review is the owner's only once the save is confirmed; a cancel leaves any earlier review intent as it was.
export function reviewPrefs() {
  return saveLayer(true);
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
    if (key.startsWith("prefs.")) {  // R15: a blank value clears the layer's own preference, so the field inherits
      const field = key.slice(6);
      const mine = { ...(next.prefs ?? {}), [field]: prefValue(field, value) };
      next.prefs = Object.values(mine).some((v) => v !== null) ? mine : null;
      continue;
    }
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
    if (key.startsWith("spot.")) {
      const field = key.slice(5), mine = { ...(next.spotter ?? {}) };
      const number = NUMBERS.includes(field) || CREDITS.includes(field);
      mine[field] = value === "" ? null : number ? typedNumber(field, value)
        : field === "looks" ? value.split(",").map((l) => l.trim()).filter(Boolean) : value;
      next.spotter = Object.values(mine).some((v) => v !== null) ? mine : null;
      continue;
    }
    if (key === "pr_marker" || USER_KEYS.includes(key)) {
      next[key] = value ? value === "on" : null;
      continue;
    }
    const [role, field] = key.split(".");
    const number = (!NUMBERS.includes(field) && !CREDITS.includes(field)) || value === "" ? null
      : typedNumber(field, value);
    if (role === "machine") {  // Global's machine settings (2026-10-23): "true"/"false" for the switches
      const flag = value === "" ? null : value === "true";
      const list = value === "" ? null : value === "none" ? [] : value.split(",").map((f) => f.trim()).filter(Boolean);
      const mine = { ...(next.machine ?? {}), [field]: field.startsWith("update_") ? flag
        : field === "enrolled_chats" ? list : number ?? (value || null) };
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

export function save() {
  return saveLayer(false);
}

async function saveLayer(review) {
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
  if (review) state.prefsReview = true;  // confirmed: from now on it is sent until it is published
  // While the write and its follow-up read run, the page shows only that it is saving: no earlier notice stands as
  // this save's outcome. The outcome is shown once it is settled, together with the save button taking a retry.
  let error = "", status = "";
  state.saving = true;
  state.error = "";
  state.status = "Saving…";
  show();
  try {
    state.loaded = await call(`/config/${layer}`,
      { method: "PUT", body: { rev: state.loaded[`${layer}_rev`], layer: edited(layer),
        prefs_reviewed: layer === "project" && state.prefsReview }, timeout: WRITE });
    if (layer === "project" && !state.loaded.unpublished) state.prefsReview = false;  // kept until published
    for (const [key, value] of Object.entries(sent)) if (drafts[layer][key] === value) delete drafts[layer][key];
    error = state.loaded.notice ?? "";
    const whose = { global: "the global", machine: "this machine's" }[layer]
      ?? (named() ? `${named()}'s` : "this project's");
    status = `Saved ${whose} settings. They apply to the next session.`;
    await readAcross();
  } catch (e) {
    error = e.message;
    if (e.status === 409 && await reload()) {
      await readAcross();
      error = `${e.message}. The page loaded the current settings and kept your unsaved edits; `
        + "check them and save again.";
    }
  } finally {
    state.saving = false;
    state.error = error ? error.charAt(0).toUpperCase() + error.slice(1) : "";
    state.status = status;
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
