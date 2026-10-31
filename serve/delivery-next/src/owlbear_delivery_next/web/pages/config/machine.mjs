import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { call, here, loaded as clones, project as current } from "/assets/ui.mjs";
import { CREDITS, INHERIT, SOURCES, WRITE, state, show, notify, typedNumber, turns } from "./state.mjs";
import { button } from "./cells.mjs";
import { edit, own, layerValue } from "./layers.mjs";

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
  retro_run_credit_limit: "Retro: credit limit per run (credits)",
  replay_run_credit_limit: "Spotter cases: credit limit per paid replay run (credits)",
  retro_after_change: "Retro after a Change ends (the Improvement button always runs)",
  retro_when_idle: "Retro over finished enrolled chats when idle",
  enrolled_chats: "Enrolled chats: workspace folders whose chats the Spotter and Retro may read, comma-separated; "
    + "none for no chats",
  update_check_hours_owlbear: "Hours between checks for a newer OwlBear (it also checks at launch)",
  update_check_hours_pds: "Hours between checks for a newer Porsche Design System (it also checks at launch)",
  update_check_hours_impeccable: "Hours between checks for a newer Impeccable (it also checks at launch)",
};
const CHOICES = { channel: CHANNELS, update_when_idle: SWITCH, update_while_paused: SWITCH,
  curate_after_merge: CURATE, curate_when_idle: CURATE, retro_after_change: CURATE, retro_when_idle: CURATE };
// Typed, not chosen.
const TYPED = ["sessions", "retro_run_credit_limit", "replay_run_credit_limit", "enrolled_chats",
  "update_check_hours_owlbear", "update_check_hours_pds", "update_check_hours_impeccable"];

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

// A typed number is kept as typed until the save, so "0.0" on the way to "0.05" stays as it is; this is what is sent.
function sent(key, value) {
  return typeof value === "string" && TYPED.includes(key) && key !== "enrolled_chats" ? typedNumber(key, value) : value;
}

// Lists compare by content; null (inherit) and [] (none) stay apart; a typed number by what it sends.
function machineEdit(key, value) {
  const draft = { ...(state.machineDraft ?? {}), [key]: value };
  if (JSON.stringify(sent(key, value)) === JSON.stringify(state.machine.settings[key] ?? null)) delete draft[key];
  state.machineDraft = Object.keys(draft).length ? draft : null;
  show();
}

// Whether the edited layer has an unsaved edit of *key*: Global's value for every machine, else this machine's own.
function moved(key) {
  if (state.layer === "machine") return Boolean(state.machineDraft && key in state.machineDraft);
  if (state.layer !== "global") return false;  // a project holds no machine setting
  return JSON.stringify(layerValue("global", `machine.${key}`)) !== JSON.stringify(state.loaded.global?.machine?.[key]
    ?? null);
}

// What this machine would use once the edited layer is saved: its own value, else Global's, else unset. On Global
// its own is the saved one: a draft of This machine is no edit of Global's.
function machineInUse(key) {
  const global = state.layer === "global", mine = global ? state.machine.settings[key] : machineValue(key);
  if (mine !== null && mine !== undefined) return { value: sent(key, mine), from: "machine" };
  const shared = global ? layerValue("global", `machine.${key}`) : state.machine.resolved?.shared?.[key];
  return { value: shared ?? null, from: shared === null || shared === undefined ? undefined : "global" };
}

// Where a setting in force comes from; an unset one says nothing here, its name is red (GW8RT6). While the edited
// layer has an unsaved edit of it, what the save would give (#809).
function machineSource(key) {
  const r = state.machine.resolved ?? {}, edited = moved(key);
  const { value, from } = edited ? machineInUse(key) : { value: r[key], from: r.sources?.[key] };
  const line = SOURCES[from] ? `in use: ${said(key, value)}, from ${SOURCES[from]}` : edited ? "in use: unset" : "";
  return line ? html`<p-text size="xs" color="contrast-medium">${line}</p-text>` : nothing;
}

// One machine setting with its name shown, red while no layer sets it (GW8RT6): a PDS label cannot be coloured, so
// the control keeps it for assistive technology only. The unset list links to it by its id.
function machineRow(key, label, control, note = nothing) {
  const unset = (state.machine.resolved?.missing ?? []).includes(key);
  return html`<div class="field" id=${`set-machine-${key}`} tabindex="-1"><p-text size="sm" aria-hidden="true"
    color=${unset ? "error" : nothing}>${label}</p-text>${control}${note}</div>`;
}

// This machine's own value of one setting: inherit Global's, or its own. A project holds none: it shows the value in
// use read-only, with where it is set (#809).
function ownControl(key) {
  const below = `inherit (${said(key, state.machine.resolved?.shared?.[key])})`, value = machineValue(key);
  const common = { disabled: state.machineSaving };
  let control;
  if (TYPED.includes(key)) {
    const list = key === "enrolled_chats";
    // The text stays as typed until saved, whether or not it changes the value: a comma or a space in a list, and
    // "20.0" on the way to "20.05" where 20 is saved, are never lost.
    const count = (e) => {
      const raw = e.target.value ?? "", v = raw.trim();
      state.machineText = { ...(state.machineText ?? {}), [key]: raw };
      machineEdit(key, v === "" ? null : list ? (v === "none" ? [] : v.split(",").map((f) => f.trim()).filter(Boolean))
        : v);
    };
    const typedText = state.machineText?.[key];  // as typed, shown only while it still means the field's value now
    const items = (t) => JSON.stringify(t.split(",").map((f) => f.trim()).filter(Boolean));
    const same = (t) => (list ? items(t) === JSON.stringify(value ?? [])
      : JSON.stringify(sent(key, t.trim())) === JSON.stringify(sent(key, value)));
    const fresh = value === null || value === undefined ? "" : list ? said(key, value) : String(value);
    const shown = typedText !== undefined && (typedText.trim() === "none" ? Array.isArray(value) && !value.length
      : typedText.trim() === "" ? value === null : same(typedText)) ? typedText : fresh;
    control = html`<p-input-text id=${`machine-${key}`} label=${MACHINE_LABELS[key]} hide-label="true"
      inputmode=${list ? nothing : CREDITS.includes(key) ? "decimal" : "numeric"} placeholder=${below}
      .value=${live(shown)}
      ?disabled=${common.disabled} @input=${count} @change=${count}></p-input-text>`;
  } else {
    const pick = (e) => {
      const v = e.target.value;
      machineEdit(key, v === INHERIT ? null : CHOICES[key] === SWITCH ? v === "true" : v);
    };
    control = html`<p-select id=${`machine-${key}`} label=${MACHINE_LABELS[key]} hide-label="true"
      .value=${live(value === null || value === undefined ? INHERIT : String(value))} ?disabled=${common.disabled}
      @change=${pick}>${[[INHERIT, below], ...CHOICES[key]].map(([v, text]) =>
        html`<p-select-option value=${v}>${text}</p-select-option>`)}</p-select>`;
  }
  return machineRow(key, MACHINE_LABELS[key], control, machineSource(key));
}

function heldElsewhere(key) {
  const value = state.machine.resolved?.[key], unset = value === null || value === undefined;
  const control = TYPED.includes(key)
    ? html`<p-input-text id=${`machine-${key}`} label=${MACHINE_LABELS[key]} hide-label="true" placeholder="unset"
      .value=${live(unset ? "" : said(key, value))} disabled></p-input-text>`
    : html`<p-select id=${`machine-${key}`} label=${MACHINE_LABELS[key]} hide-label="true"
      .value=${live(unset ? INHERIT : String(value))} disabled>${[[INHERIT, "unset"], ...CHOICES[key]]
        .map(([v, text]) => html`<p-select-option value=${v}>${text}</p-select-option>`)}</p-select>`;
  return machineRow(key, MACHINE_LABELS[key], control, html`${machineSource(key)}<p-text size="sm"
    color="contrast-medium">set on This machine or Global</p-text>`);
}

// Global's value of one setting, edited in the global layer and saved with it; clearing it leaves it unset (SEXPFT).
function sharedControl(key) {
  const draftKey = `machine.${key}`, value = own(draftKey), label = `Every machine: ${MACHINE_LABELS[key]}`;
  const warning = value.trim() ? nothing
    : html`<p-text size="sm" color="warning">Unset: every machine must then set its own</p-text>`;
  if (TYPED.includes(key)) {
    return machineRow(key, label, html`<p-input-text id=${`global-machine-${key}`} label=${label} hide-label="true"
      data-key=${draftKey} inputmode=${key === "enrolled_chats" ? nothing : CREDITS.includes(key) ? "decimal"
        : "numeric"} placeholder="Unset" .value=${live(value)} ?disabled=${state.saving}
      @input=${(e) => edit(draftKey, e.target.value ?? "")}></p-input-text>`, html`${machineSource(key)}${warning}`);
  }
  return machineRow(key, label, html`<p-select id=${`global-machine-${key}`} label=${label} hide-label="true"
    data-key=${draftKey} .value=${live(value || INHERIT)} ?disabled=${state.saving}
    @change=${(e) => edit(draftKey, e.target.value)}>${[[INHERIT, "Unset"], ...CHOICES[key]].map(([v, text]) =>
      html`<p-select-option value=${v}>${text}</p-select-option>`)}</p-select>`, html`${machineSource(key)}${warning}`);
}

function machineControls() {
  const keys = Object.keys(MACHINE_LABELS);
  if (state.layer === "global") {
    return html`<p-text id="machine-global">Every machine's settings: each machine follows these unless it sets
      its own (choose This machine above to set this machine's). Save them with the global
      defaults.</p-text>${keys.map(sharedControl)}`;
  }
  const notice = state.machine.resolved?.notice, pending = state.machine.pending;
  return html`${notice ? html`<p-text id="machine-notice" size="xs" color="error">${notice}</p-text>` : nothing}
    ${pending ? html`<p-text id="machine-pending" color="error">Moving this machine's settings into the global ones
      is not done: ${pending}. OwlBear tries again at its next start (<code>owlbear restart</code>); until then
      this machine keeps its own values.</p-text>` : nothing}
    ${keys.map((key) => (state.layer === "machine" ? ownControl : heldElsewhere)(key))}
    ${state.layer === "machine" ? html`<div class="row">${button("Save machine settings", saveMachine, {
      busy: state.machineSaving, variant: state.machineDraft ? "primary" : "secondary",
      disabled: !state.machineDraft })}</div>` : nothing}`;
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
    accept(await call("/machine/settings", { method: "PUT", machine: true, timeout: WRITE,
      body: { rev: state.machine.settings_rev, settings: { ...state.machine.settings, ...Object.fromEntries(
        Object.entries(state.machineDraft).map(([key, v]) => [key, sent(key, v)])) } } }));
    state.machineDraft = null;
    state.machineText = null;
    state.status = "Saved this machine's settings.";
  } catch (e) {
    if (e.status === 409) await call("/machine", { machine: true }).then(accept, () => undefined);
    notify(e.status === 409 ? `${e.message}. The page loaded them again and kept your edits; check them and save `
      + "again." : e.message);
  } finally {
    state.machineSaving = false;
    state.machineWrites += 1;
    show();
  }
}

// One template whether or not the machine is read yet, so a heading an address focused keeps the focus once it is. A
// read that fails after one succeeded leaves the values read before, saying so.
export function machineSection() {
  return html`<section class="panel" aria-labelledby="machine-title">
    <p-heading size="lg"><h2 id="machine-title" tabindex="-1">This machine</h2></p-heading>
    ${state.machine && state.machineUnread ? html`<p-text id="machine-stale" role="status">Could not read this
      machine's settings again: ${state.machineUnread}. These are the ones read before; the page tries again when the
      machine's state changes.</p-text>` : nothing}
    ${state.machine ? machineBody(state.machine) : html`<p-text id="machine-unread" role="status">${!clones()
      ? "Only the machine host's Settings page shows this machine's settings." : state.machineUnread
        ? `Could not read this machine's settings: ${state.machineUnread}. The page tries again when the machine's `
          + "state changes." : "Reading this machine's settings…"}</p-text>`}
  </section>`;
}

function machineBody(m) {
  const since = m.resumed_at ? `, resumed ${new Date(m.resumed_at).toLocaleString()}` : "";
  return html`<p-text id="machine-run">Delivery ${m.paused ? "is paused: press Resume above"
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
    <p-text id="machine-owlbear" size="sm">The updates themselves, with their steps and Search for updates, are in
      Menu → Updates: <a href=${here({}, "/updates/owlbear")}>OwlBear</a>,
      <a href=${here({}, "/updates/pds")}>Porsche Design System</a> and
      <a href=${here({}, "/updates/impeccable")}>Impeccable</a>.</p-text>`;
}

async function removeLegacy() {
  if (!(await ask({ title: "Remove the old runtime?", yes: "Remove it", no: "Keep it", destructive: true,
    now: `Delivery deletes ${state.machine.legacy.join(", ")}, the runtime folder from before the first update.`,
    then: "Nothing runs it any more; OwlBear runs from its installed versions.",
    after: "It cannot be brought back; a later version is installed from GitHub as usual.",
    instead: "It stays where it is." }))) return;
  try {
    accept(await call("/machine/legacy/remove", { method: "POST", machine: true, timeout: WRITE }));
    state.status = "Removed the old runtime.";
  } catch (e) {
    notify(e.message);
  }
  show();
}

const machineReads = turns(), acrossReads = turns();  // reads overlap: two refreshes, a save's and a refresh's

// The machine's values, or why they could not be read, unless a machine save ran during this read or a newer read has
// answered; then that answer stands.
export async function readMachine() {
  const writes = state.machineWrites, n = machineReads.ask();
  if (state.machineSaving) return;
  let failed = "";
  const read = await call("/machine", { machine: true }).catch((e) => {
    failed = e.message;
    return undefined;
  });
  if (state.machineSaving || writes !== state.machineWrites) return;
  if (read === undefined) {
    if (machineReads.newer(n)) state.machineUnread = failed;
  } else if (machineReads.take(n)) accept(read);  // typed text stays: it shows only while its items are its own
}

// The machine's values as the host answered them, so a read that failed before no longer speaks for them.
function accept(machine) {
  state.machine = machine;
  state.machineUnread = "";
}

// The machine host's values and every other project's settings, each shared folder once (twin clones share one).
export async function readAcross() {
  const others = (clones() ?? []).filter((p) => p.id !== current);
  if (!clones()) return;
  const n = acrossReads.ask();
  const [, ...read] = await Promise.allSettled([readMachine(), ...others.map((p) => call("/config", { of: p.id }))]);
  if (!acrossReads.take(n)) return;
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
