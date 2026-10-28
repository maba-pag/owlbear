import { html, nothing } from "/assets/lit-html/3.3.3/lit-html.js";
import { repeat } from "/assets/lit-html/3.3.3/directives/repeat.js";
import { here, HostDown, project, Restarted, Slow, shown } from "/assets/ui.mjs";
import { KEY, state, page, show, call, keyOf, parts, several, failed } from "./state.mjs";
import { hd, text } from "./widgets.mjs";
import { spentText } from "./progress.mjs";
import { badge, detailView } from "./detail.mjs";
import { startedView } from "./shaping.mjs";

const GROUPS = { you: "Needs you", working: "Delivery is working", paused: "Paused", done: "Done" };

function groupOf(label) {
  if (["Stopped", "Your turn", "Admin"].includes(label)) return "you";
  if (label === "Paused") return "paused";
  return ["Done", "Abandoned"].includes(label) ? "done" : "working";
}

function split(line) {  // the stage, then what is happening in it
  const at = line.indexOf(" \u00b7 ");
  return at < 0 ? ["", line] : [line.slice(0, at), line.slice(at + 3)];
}

function card([c, label, variant]) {
  const current = c.key === state.selected, [stage, rest] = split(c.line), step = c.progress?.line;
  const open = (event) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    choose(c.key);
  };
  const bits = [];
  if (c.now && label !== "Done" && (!step || c.now.includes(" \u00b7 "))) bits.push(split(c.now)[1]);
  if (c.step_time) bits.push(`step ${c.step_time}`);
  if (c.credits?.change || c.credits?.unknown) {
    const now = c.credits.step ? ` (this step ${c.credits.step.toFixed(2)})` : "";
    bits.push(`${spentText(c.credits.change, c.credits.unknown || 0)}${now}`);
  }
  if (c.quiet) bits.push("quiet");
  if (c.watcher?.outside) bits.push(`${c.watcher.outside} outside write${c.watcher.outside === 1 ? "" : "s"} observed`);
  return html`<li class=${current ? "card current" : "card"}>
    <div class="top"><a href=${here({ change: c.key })} class="open" data-key=${c.key}
      aria-current=${current ? "true" : nothing} @click=${open}>${c.slug}</a>
      <p-tag variant=${variant} compact="true">${label}</p-tag></div>
    ${several() ? html`<p class="meta project">${c.projectName}</p>` : nothing}
    ${step ? html`<p class="says stage">${step}</p>` : nothing}
    <p class="says">${stage && !step ? html`<span class="stage">${stage}</span> \u00b7 ` : nothing}${rest}</p>
    ${c.action && groupOf(label) !== "working" ? html`<p class="next">Next: ${c.action}</p>` : nothing}
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
  const head = !changes.length
    ? html`<p class="empty meta">No Changes yet. New Change opens a chat in VS Code where you shape the first one.</p>`
    : !groups.you.length ? html`<p class="meta">Nothing needs you right now.</p>` : nothing;
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

export function view() {
  const d = state.detail && state.detail.key === state.selected ? state.detail : null;
  return html`
    ${startedView()}
    <p-inline-notification id="error" state="error" dismiss-button="false" ?hidden=${!state.error}>${state.error
      ?? ""}</p-inline-notification>
    <p-text id="seen" color="contrast-medium" size="xs">${state.seen}</p-text>
    <section id="notes" class="panel" aria-label="Repository settings" ?hidden=${!state.notes.length}>
      ${state.notes.map((n) => text(n, { size: "xs" }))}</section>
    <div id="board" class=${state.selected ? "open" : ""}>
      <section id="list" aria-label="Changes" class=${state.stale ? "stale" : ""}>
        <div id="changes">${listView()}</div>
      </section>
      <section id="detail" aria-label="Selected Change" class=${state.stale ? "stale" : ""}>${d ? detailView(d)
        : nothing}</section>
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

// Every shown project's Changes, each with its project, and the projects' repository notes.
async function everything() {
  const projects = shown();
  if (projects === null) {  // a clone's own host: the one project it serves
    const rows = (await call("/changes")).map((c) => ({ ...c, key: c.slug, project: "", projectName: "" }));
    return [rows, (await call("/project")).notes, new Set()];
  }
  const each = await Promise.allSettled(projects.map(async (p) => [await call("/changes", undefined, p.id),
    (await call("/project", undefined, p.id)).notes]));
  const lost = (r) => r.status === "rejected" && [HostDown, Restarted, Slow].some((k) => r.reason instanceof k);
  const down = each.find(lost);
  if (down) throw down.reason;
  const rows = [], notes = [], failing = new Set();
  each.forEach((r, i) => {  // one project that cannot be read keeps its last Changes and says why; the others go on
    const p = projects[i], named = (n) => (projects.length > 1 ? `${p.name}: ${n}` : n);
    if (r.status === "rejected") {
      failing.add(p.id);
      rows.push(...(state.changes ?? []).filter((c) => c.project === p.id));
      notes.push(named(`not read just now (${r.reason.message}); its Changes show as last read`));
      return;
    }
    const [changes, said] = r.value;
    rows.push(...changes.map((c) => ({ ...c, key: keyOf(p.id, c.slug), project: p.id, projectName: p.name })));
    notes.push(...said.map(named));
  });
  return [rows, notes, failing];
}

export async function refresh() {
  if (page.busy) {
    page.again = true;  // a selection or an action while a refresh runs gets its own refresh after it
    return;
  }
  page.busy = true;
  try {
    const [rows, notes, failing] = await everything();
    [state.changes, state.notes] = [rows, notes];
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
      if (key === state.selected) state.detail = d;  // the person may have chosen another Change meanwhile
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
