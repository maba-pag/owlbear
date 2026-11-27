import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { repeat } from "/assets/lit-html/3.3.3/directives/repeat.js";
import { statusLine } from "/assets/page/config/unset.mjs";
import {
  OWN_TAG, blockedOf, displayName, here, HostDown, isOwn, loaded, project, Restarted, Slow, shown,
} from "/assets/ui.mjs";
import { holding } from "/assets/page/sending/feedback.mjs";
import { KEY, state, page, show, call, keyOf, parts, several, failed } from "./state.mjs";
import { hd, text } from "./widgets.mjs";
import { spentText } from "./progress.mjs";
import { short, split } from "./activity.mjs";
import { badge, detailView, releaseLook } from "./detail.mjs";
import { startedView } from "./shaping.mjs";
import { elsewhereBanner } from "./elsewhere.mjs";
import { due } from "./tooluse.mjs";

const GROUPS = { you: "Needs you", working: "Delivery is working", paused: "Paused", done: "Done" };

function groupOf(label) {
  if (["Stopped", "Your turn", "Admin"].includes(label)) return "you";
  if (label === "Paused") return "paused";
  return ["Done", "Abandoned"].includes(label) ? "done" : "working";
}

function card([c, label, variant]) {
  const line = statusLine(c), whole = c.error || line !== c.line;
  // a clamped card starts each paragraph on a new line: a blank line would cost one of its three (#1220)
  const current = c.key === state.selected, [stage, rest] = split(whole ? line : short(line).replace(/\n{2,}/g, "\n"));
  const step = c.progress?.line;
  const open = (event) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    choose(c.key);
  };
  const bits = [];
  if (c.now && groupOf(label) === "working" && (!step || c.now.includes(" \u00b7 "))) bits.push(split(short(c.now))[1]);
  if (c.step_time) bits.push(`step ${c.step_time}`);
  if (c.credits?.change || c.credits?.unknown) {
    const now = c.credits.step ? ` (this step ${c.credits.step.toFixed(2)})` : "";
    bits.push(`${spentText(c.credits.change, c.credits.unknown || 0)}${now}`);
  }
  if (c.quiet) bits.push("quiet");
  if (c.watcher?.outside) bits.push(`${c.watcher.outside} outside write${c.watcher.outside === 1 ? "" : "s"} observed`);
  const own = c.own ? html` <p-tag compact="true">${OWN_TAG}</p-tag>` : nothing;
  return html`<li class=${current ? "card current" : "card"}>
    <div class="top"><a href=${here({ change: c.key })} class="open" data-key=${c.key}
      aria-current=${current ? "true" : nothing} @click=${open}>${c.title || c.slug}</a>
      <p-tag variant=${variant} compact="true">${label}</p-tag></div>
    ${c.title || several() ? html`<p class="meta">${c.title ? c.slug : ""}${c.title && several() ? " \u00b7 " : ""}${
      several() ? html`<span class="project">${c.projectName}</span>${own}` : nothing}</p>` : nothing}
    ${step ? html`<p class="says stage">${step}</p>` : nothing}
    <p class=${whole ? "says whole" : "says"}>${stage && !step && stage !== label
      ? html`<span class="stage">${stage}</span> \u00b7 ` : nothing}${rest}</p>
    ${c.action && groupOf(label) !== "working" ? html`<p class="next">Next: ${c.action}</p>` : nothing}
    ${current ? nothing : releaseLook(c)}
    ${bits.length ? html`<p class="meta">${bits.join(" \u00b7 ")}</p>` : nothing}
    ${(c.overlaps || []).map((o) => html`<p class="meta">${o}</p>`)}
    ${(c.decisions || []).map((d) => html`<p class="meta">${d}</p>`)}
  </li>`;
}

function grouped() {
  const groups = { you: [], working: [], paused: [], done: [] };
  for (const c of state.changes ?? []) {
    const [variant, label] = badge(c);
    groups[groupOf(label)].push([c, label, variant]);
  }
  groups.you.sort((a, b) => (b[1] === "Stopped") - (a[1] === "Stopped"));
  return groups;
}

export function youCount() {
  return state.changes ? grouped().you.length : 0;
}

function listView() {
  const changes = state.changes, groups = grouped();
  if (!changes) return nothing;
  const head = state.unread.size ? nothing  // a project that was not read may hold what these would deny
    : !changes.length
      ? html`<p class="empty meta">No Changes yet. New Change opens a chat in VS Code where you shape the first
        one.</p>`
      : !groups.you.length ? html`<p class="says" id="nothing-yours">Nothing needs you right now.</p>` : nothing;
  const toggled = (e) => { state.doneOpen = e.target.open; };
  return html`${head}${Object.entries(GROUPS).map(([key, title]) => {
    if (!groups[key].length) return nothing;
    const said = `${title} (${groups[key].length})`;
    const cards = html`<ul class="cards">${repeat(groups[key], ([c]) => c.key, card)}</ul>`;
    if (key !== "done") return html`<section class="group">${hd(2, said, "md")}${cards}</section>`;
    const open = state.doneOpen || groups.done.some(([c]) => c.key === state.selected);
    return html`<details class="group" .open=${open} @toggle=${toggled}><summary>${said}</summary>${cards}</details>`;
  })}`;
}

// The projects whose work waits for their settings (#808), machine-wide whatever the page shows: a warning naming
// them, or the major error once no loaded project can start work; each says why, an unreadable reason in full.
function blockedBanner() {
  const all = loaded() ?? [], blocked = all.filter((p) => blockedOf(p.id));
  if (!blocked.length) return nothing;
  const every = blocked.length === all.length, names = blocked.map(displayName).join(", ");
  const heading = every ? "No work can be done until the unset settings are set."
    : `${names} can't start work until ${blocked.length === 1 ? "its" : "their"} settings are set.`;
  return html`<p-inline-notification id="blocked" state=${every ? "error" : "warning"} heading=${heading}
    heading-tag="h2" dismiss-button="false"><ul>${blocked.map((p) => html`<li><a href=${here({ project: p.id,
      change: "" }, "/config")}>${displayName(p)}</a>: ${blockedOf(p.id)}</li>`)}</ul></p-inline-notification>`;
}

// What shows as last read takes no activation, by key as little as by pointer: a focused button in it must not send.
// It stays readable for a screen reader, so it is not made inert.
const held = {
  capture: true,
  handleEvent(event) {
    if (!event.currentTarget.classList.contains("stale")) return;
    event.preventDefault();
    event.stopPropagation();
  },
};

export function view() {
  const d = state.detail && state.detail.key === state.selected ? state.detail : null;
  const old = (shows) => (state.stale || shows ? "stale" : "");
  // The way back to the list stands outside the detail: it works while the detail is as last read, or not shown yet.
  const back = state.selected ? html`<p-button-pure type="button" icon="arrow-left" class="back"
    @click=${() => choose(null)}>All Changes</p-button-pure>` : nothing;
  return html`
    ${startedView()}
    <p-inline-notification id="error" state="error" dismiss-button="false" ?hidden=${!state.error}>${state.error
      ?? ""}</p-inline-notification>
    ${blockedBanner()}
    ${elsewhereBanner()}
    <p-text id="seen" color="contrast-medium" size="xs">${state.seen}</p-text>
    <section id="notes" class="panel" aria-label="Repository settings" ?hidden=${!state.notes.length}>
      ${state.notes.map((n) => text(n))}</section>
    <div id="board" class=${state.selected ? "open" : ""}>
      <section id="list" aria-label="Changes" class=${old(false)} @click=${held}>
        <div id="changes">${listView()}</div>
      </section>
      <div id="chosen">${back}
        <section id="detail" aria-label="Selected Change" class=${old(d && state.unread.has(d.project))}
          @click=${held}>${d ? detailView(d) : nothing}</section>
      </div>
    </div>`;
}

function reveal(target) {
  if (matchMedia("(max-width: 63.99rem)").matches) return window.scrollTo(0, 0);
  const top = target.getBoundingClientRect().top;
  if (top < 0 || top > innerHeight / 2) target.scrollIntoView({ block: "start" });
}

// The heading takes focus only once its PDS wrapper has rendered; a hidden element cannot be focused.
function focusHeading() {
  const target = document.getElementById("detail");
  const wrapper = target.querySelector("p-heading"), name = target.querySelector("h2");
  if (!name) return;
  Promise.resolve(wrapper?.componentOnReady?.()).then(() => {
    if (name.isConnected) name.focus({ preventScroll: true });
  });
  reveal(target);
}

// A key the page can open: a bare slug from an older link names the page's project, if it names one.
export function wanted(key) {
  if (!key || !KEY.test(key)) return null;
  return key.includes("/") || !project ? key : keyOf(project, key);
}

export function choose(key, push = true) {
  const was = state.selected;
  state.selected = wanted(key);
  page.arrived = Boolean(state.selected);
  if (state.selected !== was) state.started = null;  // a note belongs to its Change
  if (push && state.selected !== was) {
    history.pushState(null, "", here({ change: state.selected }));
  }
  show();
  if (!state.selected && was) document.querySelector(`#changes a[data-key="${CSS.escape(was)}"]`)?.focus();
  refresh();
}

// Every shown project's Changes, each with its project, and the projects' repository notes. A project's two reads
// go out together, so one that does not answer holds the others' rows for the time of one read.
async function everything() {
  const projects = shown();
  const both = (of) => Promise.all([call("/changes", undefined, of), call("/project", undefined, of)]);
  if (projects === null) {  // a clone's own host: the one project it serves
    const [changes, said] = await both();
    return [changes.map((c) => ({ ...c, key: c.slug, project: "", projectName: "" })), said.notes, new Map()];
  }
  const each = await Promise.allSettled(projects.map((p) => both(p.id)));
  const lost = (r, ...kinds) => r.status === "rejected" && kinds.some((k) => r.reason instanceof k);
  // The host is gone, or no project answered in time: the whole page says so. One slow project of several does not.
  const down = each.find((r) => lost(r, HostDown, Restarted)) ?? (each.every((r) => lost(r, Slow)) ? each[0] : null);
  if (down) throw down.reason;
  const rows = [], notes = [], failing = new Map();
  each.forEach((r, i) => {  // one project that cannot be read keeps its last Changes and says why; the others go on
    const p = projects[i], named = (n) => (projects.length > 1 ? `${displayName(p)}: ${n}` : n);
    if (r.status === "rejected") {
      const kept = (state.changes ?? []).filter((c) => c.project === p.id);
      failing.set(p.id, r.reason.message);
      rows.push(...kept);
      notes.push(named(`not read just now (${r.reason.message})${kept.length ? "; its Changes show as last read"
        : ""}`));
      return;
    }
    const [changes, said] = r.value;
    rows.push(...changes.map((c) => ({ ...c, key: keyOf(p.id, c.slug), project: p.id, projectName: displayName(p),
      own: isOwn(p) })));
    notes.push(...said.notes.map(named));
  });
  return [rows, notes, failing];
}

export async function refresh() {
  if (holding()) {  // a send's form stays as it is until its answer and checkmark: the send rereads after them
    page.skipped = true;
    return;
  }
  if (page.busy) {
    page.again = true;  // a selection or an action while a refresh runs gets its own refresh after it
    return;
  }
  page.busy = true;
  page.skipped = false;
  try {
    const [rows, notes, failing] = await everything();
    if (holding()) {
      page.skipped = true;
      return;
    }
    [state.changes, state.notes, state.unread] = [rows, notes, failing];
    const unread = state.selected && failing.has(parts(state.selected)[0]);  // absent only once its project answers
    if (state.selected && !unread && !rows.some((c) => c.key === state.selected)) {  // gone, or a stale link
      state.selected = null;
      history.replaceState(null, "", here({ change: "" }));
    }
    page.lastSeen = new Date();
    state.error = null;
    state.seen = "";
    state.stale = false;
    const key = state.selected;
    if (key && unread) {
      // its project did not answer: the detail stays as last read
    } else if (key) {
      const [of, slug] = parts(key), d = await call(`/changes/${encodeURIComponent(slug)}`, undefined, of);
      const row = state.changes.find((c) => c.key === key);
      Object.assign(d, { key, project: of, projectName: row?.projectName ?? "" });
      if (holding()) {  // read before a send's answer: it may already lack the form held for its checkmark
        page.skipped = true;
        return;
      }
      if (key === state.selected) state.detail = d;  // the person may have chosen another Change meanwhile
      due();
    } else {
      state.detail = null;
    }
    show();
    if (page.arrived && state.detail?.key === state.selected) {
      page.arrived = false;
      focusHeading();
    }
  } catch (e) {
    failed(e);
  } finally {
    page.busy = false;
    if (page.again) {
      page.again = false;
      refresh();
    }
  }
}
