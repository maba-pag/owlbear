import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { call, loaded as clones, project as current } from "/assets/ui.mjs";
import { INHERIT, SOURCES, WRITE, state, show, notify } from "./state.mjs";
import { button } from "./cells.mjs";
import { edit, own } from "./layers.mjs";

// The machine settings: Global's for every machine, each machine may set its own (D-01M5MZKEPPVMFC9HK795MMG91B);
// changed only here or in a terminal, never in a project's layer (TD-243).
const CHANNELS = [["minor", "Every minor version (v0.1, v0.2 …)"], ["major", "Major versions only (v1, v2 …)"]];
// Each automatic curation trigger: off, on, or on even while paused; the Maintenance button always runs (2026-10-23).
const CURATE = [["off", "Off"], ["on", "On, not while paused"], ["paused", "On, even while paused"]];
const SWITCH = [["true", "On"], ["false", "Off"]];
const MACHINE_LABELS = {
  channel: "Versions this machine takes", update_when_idle: "Update itself when idle",
  update_while_paused: "Update itself while paused", curate_after_merge: "Curate memory after a merge",
  curate_when_idle: "Curate memory when idle (the Maintenance button always runs)",
  sessions: "Agent sessions at once on this machine, across its projects",
  spotter_budget: "Spotter: credits a day", retro_budget: "Retro: credits a day",
  retro_verbose_cap: "Retro: credits a day it may spend turning the Spotter's verbose on",
  retro_after_change: "Retro after a Change ends (the Improvement button always runs)",
  retro_when_idle: "Retro over finished enrolled chats when idle",
  enrolled_chats: "Enrolled chats: workspace folders whose chats the Spotter and Retro may read, comma-separated; "
    + "none for no chats",
};
const CHOICES = { channel: CHANNELS, update_when_idle: SWITCH, update_while_paused: SWITCH,
  curate_after_merge: CURATE, curate_when_idle: CURATE, retro_after_change: CURATE, retro_when_idle: CURATE };
const TYPED = ["sessions", "spotter_budget", "retro_budget", "retro_verbose_cap", "enrolled_chats"];  // typed, not chosen

// A machine setting's value in words; "unset" where none is set.
function said(key, v) {
  if (v === null || v === undefined || v === "") return "unset";
  if (Array.isArray(v)) return v.join(", ") || "none";
  return (CHOICES[key] ?? []).find(([c]) => c === String(v))?.[1] ?? String(v);
}

// The machine's settings as shown: each edited one as edited, the others as saved (TD-288, TD-300); a save after
// another page's lands only the edited ones on top of that page's. ``null`` inherits Global's.
function machineValue(key) {
  return state.machineDraft && key in state.machineDraft ? state.machineDraft[key] : state.machine.settings[key];
}

// Lists compare by content; null (inherit) and [] (none) stay apart.
function machineEdit(key, value) {
  const draft = { ...(state.machineDraft ?? {}), [key]: value };
  if (JSON.stringify(value) === JSON.stringify(state.machine.settings[key] ?? null)) delete draft[key];
  state.machineDraft = Object.keys(draft).length ? draft : null;
  show();
}

// Where a setting in force comes from, or that it is unset: an error, as nothing that needs it runs (2026-10-23).
function machineSource(key) {
  const r = state.machine.resolved ?? {}, from = SOURCES[r.sources?.[key]];
  if (!from) {
    return html`<p-text size="xs" color="error">unset: set it here or for every machine in the global layer;
      what needs it does not run until then</p-text>`;
  }
  return html`<p-text size="xs" color="contrast-medium">in use: ${said(key, r[key])}, from ${from}</p-text>`;
}

// This machine's own value of one setting: inherit Global's, or its own.
function ownControl(key) {
  const below = `inherit (${said(key, state.machine.resolved?.shared?.[key])})`, value = machineValue(key);
  const common = { disabled: state.machineSaving };
  let control;
  if (TYPED.includes(key)) {
    const list = key === "enrolled_chats";
    const count = (e) => {  // a list keeps the text as typed until saved, so a comma or a space is never lost
      const raw = e.target.value ?? "", v = raw.trim();
      if (list) state.machineText = { ...(state.machineText ?? {}), [key]: raw };
      machineEdit(key, v === "" ? null : list ? (v === "none" ? [] : v.split(",").map((f) => f.trim()).filter(Boolean))
        : /^\d+$/.test(v) ? Number(v) : v);
    };
    const typedText = state.machineText?.[key];  // as typed until a save, even where it equals the saved list
    const shown = typedText ?? (value === null || value === undefined ? "" : list ? said(key, value) : String(value));
    control = html`<p-input-text id=${`machine-${key}`} label=${MACHINE_LABELS[key]}
      inputmode=${list ? nothing : "numeric"} placeholder=${below} .value=${live(shown)}
      ?disabled=${common.disabled} @input=${count} @change=${count}></p-input-text>`;
  } else {
    const pick = (e) => {
      const v = e.target.value;
      machineEdit(key, v === INHERIT ? null : CHOICES[key] === SWITCH ? v === "true" : v);
    };
    control = html`<p-select id=${`machine-${key}`} label=${MACHINE_LABELS[key]}
      .value=${live(value === null || value === undefined ? INHERIT : String(value))} ?disabled=${common.disabled}
      @change=${pick}>${[[INHERIT, below], ...CHOICES[key]].map(([v, text]) =>
        html`<p-select-option value=${v}>${text}</p-select-option>`)}</p-select>`;
  }
  return html`<div>${control}${machineSource(key)}</div>`;
}

// Global's value of one setting, edited in the global layer and saved with it.
function sharedControl(key) {
  const draftKey = `machine.${key}`, value = own(draftKey), label = `Every machine: ${MACHINE_LABELS[key]}`;
  if (TYPED.includes(key)) {
    return html`<p-input-text id=${`global-machine-${key}`} label=${label} data-key=${draftKey}
      inputmode=${key === "enrolled_chats" ? nothing : "numeric"} placeholder="unset" .value=${live(value)}
      ?disabled=${state.saving}
      @input=${(e) => edit(draftKey, e.target.value ?? "")}></p-input-text>`;
  }
  return html`<p-select id=${`global-machine-${key}`} label=${label} data-key=${draftKey}
    .value=${live(value || INHERIT)} ?disabled=${state.saving} @change=${(e) => edit(draftKey, e.target.value)}>
    ${[[INHERIT, "unset"], ...CHOICES[key]].map(([v, text]) =>
      html`<p-select-option value=${v}>${text}</p-select-option>`)}</p-select>`;
}

function machineControls() {
  const keys = Object.keys(MACHINE_LABELS);
  if (state.layer === "global") {
    return html`<p-text id="machine-global">Every machine's settings: each machine follows these unless it sets
      its own (choose This project or This machine above to see this machine's). Save them with the global
      defaults.</p-text>${keys.map(sharedControl)}`;
  }
  const notice = state.machine.resolved?.notice, pending = state.machine.pending;
  return html`${notice ? html`<p-text id="machine-notice" size="xs" color="error">${notice}</p-text>` : nothing}
    ${pending ? html`<p-text id="machine-pending" color="error">Moving this machine's settings into the global ones
      is not done: ${pending}. OwlBear tries again at its next start (<code>owlbear restart</code>); until then
      this machine keeps its own values.</p-text>` : nothing}
    ${keys.map(ownControl)}
    <div class="row">${button("Save machine settings", saveMachine, { busy: state.machineSaving,
      disabled: !state.machineDraft })}</div>`;
}

async function saveMachine() {
  if (!state.machineDraft || state.machineSaving) return;
  const shown = (key, v) => (v === null || v === undefined ? "inherited" : said(key, v));
  if (!(await ask({
    title: "Change this machine's settings?", yes: "Save machine settings", no: "Keep editing",
    now: "These apply to this machine only:", items: Object.entries(state.machineDraft).map(([key, v]) =>
      `${MACHINE_LABELS[key] ?? key}: ${shown(key, state.machine.settings[key])} → ${shown(key, v)}`),
    then: "Delivery here follows them from now on; other machines keep theirs.",
    after: "Change them back here at any time.",
    instead: "Your edits stay unsaved on this page.",
  }))) return;
  state.machineSaving = true;  // the controls stay disabled until it ends, so no edit is made and lost meanwhile
  state.machineWrites += 1;
  show();
  try {
    state.machine = await call("/machine/settings", { method: "PUT", machine: true, timeout: WRITE,
      body: { rev: state.machine.settings_rev, settings: { ...state.machine.settings, ...state.machineDraft } } });
    state.machineDraft = null;
    state.machineText = null;
    state.status = "Saved this machine's settings.";
  } catch (e) {
    if (e.status === 409) state.machine = await call("/machine", { machine: true }).catch(() => state.machine);
    notify(e.status === 409 ? `${e.message}. The page loaded them again and kept your edits; check them and save `
      + "again." : e.message);
  } finally {
    state.machineSaving = false;
    state.machineWrites += 1;
    show();
  }
}

export function machineSection() {
  const m = state.machine;
  if (!m) return nothing;
  const since = m.resumed_at ? `, resumed ${new Date(m.resumed_at).toLocaleString()}` : "";
  return html`<section class="panel" aria-labelledby="machine-title">
    <p-heading size="lg"><h2 id="machine-title">This machine</h2></p-heading>
    <p-text id="machine-run">Delivery ${m.paused ? "is paused: press Resume above"
      : `runs${since}`}.</p-text>
    <p-text id="machine-login">Start at login: ${m.login_item}. Change it in a terminal with
      <code>owlbear autostart on</code> or <code>owlbear autostart off</code>.</p-text>
    ${machineControls()}
    ${m.legacy?.length ? html`<p-text id="machine-legacy">The runtime from before the first update is kept in
      ${m.legacy.join(", ")}; nothing runs it any more.</p-text>
      ${button("Remove the old runtime", removeLegacy, { variant: "secondary" })}` : nothing}
    <p-text id="machine-note" size="xs" color="contrast-medium">OwlBear updates itself after 15 minutes without
      use while nothing runs, announced on open pages 2 minutes ahead; Run updates now on a paused page or
      <code>owlbear update</code> updates at once.</p-text>
  </section>`;
}

async function removeLegacy() {
  if (!(await ask({ title: "Remove the old runtime?", yes: "Remove it", no: "Keep it",
    now: `Delivery deletes ${state.machine.legacy.join(", ")}, the runtime folder from before the first update.`,
    then: "Nothing runs it any more; OwlBear runs from its installed versions.",
    after: "It cannot be brought back; a later version is installed from GitHub as usual.",
    instead: "It stays where it is." }))) return;
  try {
    state.machine = await call("/machine/legacy/remove", { method: "POST", machine: true, timeout: WRITE });
    state.status = "Removed the old runtime.";
  } catch (e) {
    notify(e.message);
  }
  show();
}

// The machine's values, unless a machine save ran during this read; then the save's answer stands.
export async function readMachine() {
  const writes = state.machineWrites;
  if (state.machineSaving) return;
  const read = await call("/machine", { machine: true }).catch(() => undefined);
  if (read !== undefined && !state.machineSaving && writes === state.machineWrites) state.machine = read;
}

// The machine host's values and every other project's settings, each shared folder once (twin clones share one).
export async function readAcross() {
  const others = (clones() ?? []).filter((p) => p.id !== current);
  if (!clones()) return;
  const [, ...read] = await Promise.allSettled([readMachine(), ...others.map((p) => call("/config", { of: p.id }))]);
  const seen = new Set(state.loaded?.folder ? [state.loaded.folder] : []);
  state.others = [];
  state.unread = [];
  read.forEach((r, i) => {
    if (r.status === "rejected") return state.unread.push(`${others[i].name}: ${r.reason.message}`);
    if (r.value.folder && seen.has(r.value.folder)) return null;
    seen.add(r.value.folder);
    return state.others.push({ name: others[i].name, config: r.value });
  });
}
