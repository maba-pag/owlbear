// The menu (D-01M63C8375KV9WA6NH8K2MB8PN): the top row's burger opens PDS's drilldown with every page. The work
// pages have their own level and on phones are only here; ui.mjs's guard covers its links
// (D-01M63C8DA1D95Z7M9ZYWVYYNF7). Updates have theirs too (D-01M63C5VGFWJ709X2GA0CE8Q5B), marked when one is
// available, running or failed (D-01M63CDFXCN5SSCNNYWV2FVFVA). Settings' groups have theirs
// (D-01M63C8QQMANY46N8GMNNKH1V9).

import { html, nothing, render } from "/assets/lit-html/3.3.3/lit-html.js";
import { call, defined, here, machineState } from "/assets/ui.mjs";
import { checks, listen, update } from "/assets/page/updates/checks.mjs";
import { GROUPS } from "/assets/page/config/groups.mjs";

// The menu in its order: levels, each with its links, and links to a page beside them.
const MENU = [
  { id: "work", label: "Work", links: [["/", "Changes"], ["/backlog", "Backlog"], ["/memory", "Memory"],
    ["/decisions", "Decisions"], ["/metrics", "Metrics"], ["/improvement", "Improvement"]] },
  { id: "updates", label: "Updates", links: [["/updates/owlbear", "OwlBear"],
    ["/updates/pds", "Porsche Design System"], ["/updates/impeccable", "Impeccable"]] },
  ["/projects", "Projects"],
  { id: "settings", label: "Settings", links: GROUPS.map(([id, said]) => [`/config#${id}`, said]) },
  ["/maintenance", "Maintenance"],
];
const LEVELS = MENU.filter((entry) => !Array.isArray(entry));
const DETAIL = "owlbear-improvement-detail";  // Change pages show the Spotter's and Retro's detail while it is "on"

const menu = { open: false, level: undefined, runs: {} };
const RUNS = { impeccable: "/maintenance/pack/runs", pds: "/maintenance/pds/runs" };  // as pack.mjs reads each
const root = document.getElementById("menu");
const ENDED = ["idle", "current", "failed", "refused"];  // the OwlBear update's phases once it is not running
const TONES = { Running: "secondary", "Waiting for you": "warning", "Host stopped": "warning", Failed: "error",
  Available: "info" };

// What the menu says of an update, in words: running (or waiting for the owner, or its host stopped), failed,
// available.
function words(name) {
  const u = update(name), phase = machineState()?.update?.phase, run = menu.runs[name];
  if (name === "owlbear" && phase && !ENDED.includes(phase)) return ["Running"];
  if (run?.interrupted) return ["Host stopped"];  // it cannot go on until that project's host starts again
  if (run?.state === "running") return ["Running"];
  if (run?.state === "waiting") return ["Waiting for you"];
  const failed = (name === "owlbear" && phase === "failed") || run?.state === "failed" || Boolean(u?.reason);
  return [failed && "Failed", u?.available && "Available"].filter(Boolean);
}

// Whether *to* is this page: its path, and the Settings group shown (Overview when the address names none).
function isHere(to) {
  const [path, part] = to.split("#");
  return path === location.pathname && (!part || (location.hash || "#overview") === `#${part}`);
}

function link([path, label]) {
  const current = isHere(path), said = path.startsWith("/updates/") ? words(path.slice(9)) : [];
  return html`<p-drilldown-link ?active=${current}><a href=${here({}, path)}
    aria-current=${current ? "page" : nothing}>${label}${said.map((w) => html`<p-tag class="said" compact="true"
      variant=${TONES[w]}>${w}</p-tag>`)}</a></p-drilldown-link>`;
}

// The switch under Work: off by default; a Change page open now redraws at once (changes/improvement.mjs).
function detailSwitch() {
  const on = localStorage.getItem(DETAIL) === "on";
  const set = (e) => {
    if (e.detail?.checked === undefined || e.detail.checked === on) return;
    localStorage.setItem(DETAIL, e.detail.checked ? "on" : "off");
    dispatchEvent(new Event(DETAIL));
    show();
  };
  return html`<p-switch id="improvement-detail-switch" compact="true" .checked=${on} @change=${set} @update=${set}>
    Show the Spotter's and Retro's detail on Change pages</p-switch>`;
}

function label(l) {
  const n = l.id === "updates" ? checks.all?.available ?? 0 : 0;
  return n ? `${l.label}, ${n} available` : l.label;
}

// Whether the Impeccable and PDS updates run, wait or failed: read when the menu opens, so no page polls them for it.
async function readRun() {
  await Promise.all(Object.entries(RUNS).map(async ([name, path]) => {
    try {
      menu.runs[name] = (await call(path, { timeout: 15000, machine: true })).run;
    } catch {
      menu.runs[name] = null;  // unknown: the entry says nothing of a run rather than something stale
    }
  }));
  if (menu.open) show();
}

const item = (id) => root.querySelector(`p-drilldown-item[identifier="${id}"]`);

// PDS shows a level on its own schedule and its dialog focuses the dismiss button, so focus waits until the target
// shows, for at most a second.
async function focus(find) {
  for (let frame = 0; frame < 60; frame++) {
    await new Promise(requestAnimationFrame);
    const target = find();
    if (!target?.checkVisibility({ visibilityProperty: true })) continue;
    target.focus();
    if (target.matches(":focus")) return;
  }
}

// The menu opens at the level that holds this page, so its siblings are one step away, with focus on this page's link.
function open() {
  menu.open = true;
  menu.level = LEVELS.find((l) => l.links.some(([path]) => isHere(path)))?.id;
  show();
  readRun();
  focus(() => root.querySelector("p-drilldown a[aria-current]") ?? root.querySelector("p-drilldown a[href]"));
}

function close() {
  menu.open = false;
  show();
}

// A level opens with focus on its first link; going back puts it on the button that opened the level.
function moved(e) {
  const left = menu.level;
  menu.level = e.detail.activeIdentifier;
  show();
  focus(() => menu.level ? item(menu.level)?.querySelector("a[href]")
    : item(left)?.shadowRoot?.querySelector("p-button-pure.button"));
}

// A link the guard held (ui.mjs) leaves the page as it is; the menu closes so its reason shows under the top row. One
// to a part of this page (a Settings group on Settings) shows it, so the menu closes too.
function clicked(e) {
  const to = e.target.closest?.("a[href]");
  if (!to) return;
  const url = new URL(to.href, location.href);
  if (e.defaultPrevented || (url.hash && url.pathname === location.pathname && url.search === location.search)) close();
}

function show() {
  const marked = (checks.all?.available ?? 0) > 0;
  render(html`
    <p-button-pure type="button" icon="menu-lines" hide-label="true" aria="{'aria-haspopup': 'dialog'}"
      @click=${open}>${marked ? "Menu, updates available" : "Menu"}</p-button-pure>
    ${marked ? html`<span class="dot" id="menu-dot" aria-hidden="true"></span>` : nothing}
    <p-drilldown .open=${menu.open} .activeIdentifier=${menu.level} .aria=${{ "aria-label": "OwlBear pages" }}
      @update=${moved} @dismiss=${close} @click=${clicked}>
      ${MENU.map((e) => Array.isArray(e) ? link(e) : html`<p-drilldown-item identifier=${e.id}
        label=${label(e)}>${e.links.map(link)}${e.id === "work" ? detailSwitch() : nothing}</p-drilldown-item>`)}
    </p-drilldown>`, root);
}

if (root) {
  await defined(["p-button-pure", "p-drilldown", "p-drilldown-item", "p-drilldown-link", "p-switch", "p-tag"]);
  listen(show);
  document.addEventListener("owlbear-polled", () => show());  // the OwlBear update's phase
  show();
}
