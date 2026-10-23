import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { live } from "/assets/lit-html/3.3.3/directives/live.js";
import { call, loaded as clones, project as current } from "/assets/ui.mjs";
import { WRITE, state, show, notify } from "./state.mjs";
import { button } from "./cells.mjs";

// The machine's own values: changed only here, from a terminal, never in a settings layer (TD-243).
const CHANNELS = [["minor", "Every minor version (v0.1, v0.2 …)"], ["major", "Major versions only (v1, v2 …)"]];
// Each automatic curation trigger: off, on, or on even while paused; the Maintenance button always runs (2026-10-23).
const CURATE = [["off", "Off"], ["on", "On, not while paused"], ["paused", "On, even while paused"]];
const MACHINE_LABELS = {
  channel: "Versions this machine takes", update_when_idle: "Update itself when idle",
  update_while_paused: "Update itself while paused", curate_after_merge: "Curate memory after a merge",
  curate_when_idle: "Curate memory when idle",
  sessions: "Agent sessions at once on this machine",
};

// The machine's settings as shown: each edited one as edited, the others as saved (TD-288, TD-300); a save after
// another page's lands only the edited ones on top of that page's.
function machineValue(key) {
  return state.machineDraft && key in state.machineDraft ? state.machineDraft[key] : state.machine.settings[key];
}

function machineEdit(key, value) {
  const draft = { ...(state.machineDraft ?? {}), [key]: value };
  if (value === state.machine.settings[key]) delete draft[key];
  state.machineDraft = Object.keys(draft).length ? draft : null;
  show();
}

function machineControls() {
  const pick = (e) => machineEdit("channel", e.target.value);
  const channel = html`<p-select id="machine-channel" label="Versions this machine takes"
    .value=${live(machineValue("channel"))} ?disabled=${state.machineSaving} @change=${pick}>${CHANNELS.map(
    ([v, said]) => html`<p-select-option value=${v}>${said}</p-select-option>`)}</p-select>`;
  const curate = (key, label) => html`<p-select id=${`machine-${key}`} label=${label}
    .value=${live(machineValue(key))} ?disabled=${state.machineSaving} @change=${(e) => machineEdit(key,
      e.target.value)}>${CURATE.map(([v, said]) => html`<p-select-option value=${v}>${said}</p-select-option>`)}
    </p-select>`;
  const box = (key, label) => {
    const flip = (e) => machineEdit(key, e.target.checked === true);
    return html`<p-checkbox label=${label} .checked=${live(machineValue(key))} ?disabled=${state.machineSaving}
      @change=${flip}></p-checkbox>`;
  };
  // TD-336: the machine's total of agent sessions at once, across every project it serves.
  const count = (e) => {
    const v = (e.target.value ?? "").trim();
    machineEdit("sessions", /^\d+$/.test(v) ? Number(v) : v);
  };
  const label = "Agent sessions at once on this machine, across its projects";
  const sessions = html`<p-input-text id="machine-sessions" label=${label} inputmode="numeric"
    .value=${live(String(machineValue("sessions")))} ?disabled=${state.machineSaving} @input=${count}
    @change=${count}></p-input-text>`;
  return html`${channel}${box("update_when_idle", "Update itself when idle")}
    ${box("update_while_paused", "Update itself while paused")}
    ${curate("curate_after_merge", "Curate memory after a merge")}
    ${curate("curate_when_idle", "Curate memory when idle (the Maintenance button always runs)")}
    ${sessions}
    <div class="row">${button("Save machine settings", saveMachine, { busy: state.machineSaving,
      disabled: !state.machineDraft })}</div>`;
}

async function saveMachine() {
  if (!state.machineDraft || state.machineSaving) return;
  const said = (key, v) => (key === "channel" ? CHANNELS.find(([c]) => c === v)?.[1] ?? v
    : key.startsWith("curate_") ? CURATE.find(([c]) => c === v)?.[1] ?? v
      : typeof v === "boolean" ? (v ? "on" : "off") : String(v));
  if (!(await ask({
    title: "Change this machine's settings?", yes: "Save machine settings", no: "Keep editing",
    now: "These apply to this machine only:", items: Object.entries(state.machineDraft).map(([key, v]) =>
      `${MACHINE_LABELS[key] ?? key}: ${said(key, state.machine.settings[key])} → ${said(key, v)}`),
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
